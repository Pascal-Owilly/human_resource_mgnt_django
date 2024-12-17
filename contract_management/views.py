from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.template import Template, Context
from django.template.loader import render_to_string, get_template
from django.urls import reverse
from django.core.paginator import Paginator
from xhtml2pdf import pisa
from openpyxl import load_workbook
from jsignature.forms import JSignatureField
from .forms import ContractSignatureForm, ExcelUploadForm
from .models import ContractTemplate, Placeholder, Contract, User
import csv
import pandas as pd
import os
import tempfile
from jinja2 import Template

# User Search for Contract Signatories
@login_required
def user_search(request):
    query = request.GET.get('q', '').strip()
    if query:
        users = User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(email__icontains=query)
        )[:10]
        user_list = [
            {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "phone_number": user.phone_number,
                "email": user.email
            }
            for user in users
        ]
        return JsonResponse(user_list, safe=False)

    return JsonResponse([], safe=False)

# Create contract template view
@login_required
def create_contract_template(request):
    if request.method == 'POST':
        name = request.POST['name']
        template_content = request.POST['template_content']
        selected_placeholders = request.POST.getlist('placeholders')
        template = ContractTemplate.objects.create(name=name, template_content=template_content)
        template.placeholders.set(selected_placeholders)
        return redirect('hrms:template_list')

    placeholders = Placeholder.objects.all()
    return render(request, 'contract_management/create_template.html', {'placeholders': placeholders})

# Create contract based on template
@login_required
def create_contract(request, template_id):
    template = get_object_or_404(ContractTemplate, pk=template_id)

    if request.method == 'POST':
        placeholder_values = {
            placeholder.key: request.POST.get(placeholder.key, f"[{placeholder.name}]")
            for placeholder in template.placeholders.all()
        }
        template_content = Template(template.template_content)
        context = Context(placeholder_values)
        filled_contract = template_content.render(context)
        contract = Contract.objects.create(template=template, content=filled_contract)
        return redirect('hrms:contract_preview', contract_id=contract.id)

    return render(request, 'contract_management/create_contract.html', {'template': template})


@login_required
def render_to_pdf(template_src, context_dict={}):
    """
    Render a PDF from a given template and context data.
    """
    template = get_template(template_src)
    html = template.render(context_dict)
    result = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=result)
    if pisa_status.err:
        return HttpResponse(f'Error generating PDF: {pisa_status.err}')
    return result

@login_required
def contract_preview(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    contract_templates = ContractTemplate.objects.all()

    email_sent = contract.email_sent
    recipient_email = None
    recipient_name = None

    # Get the placeholders from the contract template
    contract_template = contract.template
    placeholders = contract_template.placeholders.all()

    # Prepare dynamic data for placeholders
    contract_data = {}
    for placeholder in placeholders:
        placeholder_key = placeholder.key

        # Dynamically fetch values based on placeholder keys
        if placeholder_key == "full_name":
            contract_data[placeholder_key] = (
                contract.user.get_full_name() if contract and contract.user else "N/A"
            )
        elif placeholder_key == "id_number":
            contract_data[placeholder_key] = (
                getattr(contract.user, "id_number", "N/A") if contract and contract.user else "N/A"
            )
        elif placeholder_key == "phone_number":
            contract_data[placeholder_key] = (
                contract.user.phone_number if contract and contract.user else "N/A"
            )
        elif placeholder_key == "employer_name":
            contract_data[placeholder_key] = settings.EMPLOYER_NAME  # Configurable setting
        elif placeholder_key == "start_date":
            contract_data[placeholder_key] = contract.created_at.strftime('%B %d, %Y') if contract else "N/A"
        elif placeholder_key == "end_date":
            contract_data[placeholder_key] = contract.end_date.strftime('%B %d, %Y') if hasattr(contract, 'end_date') else "N/A"
        else:
            # Default to placeholder key for unrecognized placeholders
            contract_data[placeholder_key] = f"[{placeholder_key} not found]"

    # Replace placeholders in the template content
    contract_content = contract_template.template_content
    for placeholder_key, replacement_value in contract_data.items():
        contract_content = contract_content.replace(f'{{{{ {placeholder_key} }}}}', replacement_value)

    # Handle form submission for email sending
    if request.method == 'POST':
        recipient_email = request.POST.get('recipient_email')
        if recipient_email:
            try:
                user = User.objects.get(email=recipient_email)
                contract.user = user
                contract.save()

                contract_review_url = request.build_absolute_uri(reverse('hrms:contract_preview', args=[contract.id]))
                subject = "Contract Notification"

                # Email content
                recipient_name = user.get_full_name().strip() or user.username
                html_message = render_to_string('contract_management/emails/contract_notification.html', {
                    'recipient_name': recipient_name,
                    'contract_id': contract.id,
                    'contract_link': contract_review_url,
                })
                plain_message = f"""
                    Hello {recipient_name},

                    You have a pending contract to review and sign.

                    Contract ID: {contract.id}
                    Please visit the following link to review and sign the contract:
                    {contract_review_url}

                    Best regards,
                """
                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient_email],
                    html_message=html_message
                )

                contract.email_sent = True
                contract.save()
                messages.success(request, f"Email sent successfully to {recipient_name} ({recipient_email}).")
                return render(request, 'contract_management/contract_preview.html', {
                    'contract': contract,
                    'contract_templates': contract_templates,
                    'success': True,
                    'recipient_name': recipient_name,
                    'recipient_email': recipient_email,
                    'contract_content': contract_content,
                })
            except User.DoesNotExist:
                messages.error(request, "User with the provided email does not exist.")
        else:
            messages.error(request, "Recipient email is required.")

    # Handle PDF generation
    if request.GET.get('generate_pdf'):
        buffer = BytesIO()
        pdf_canvas = canvas.Canvas(buffer)
        pdf_canvas.drawString(100, 800, f"Contract Preview - {contract.user.get_full_name()}")
        pdf_canvas.drawString(100, 780, contract_content[:1000])  # Example: Partial content
        pdf_canvas.showPage()
        pdf_canvas.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=contract_{contract.id}.pdf'
        return response

    # Render the preview page
    return render(request, 'contract_management/contract_preview.html', {
        'contract': contract,
        'contract_templates': contract_templates,
        'email_sent': email_sent,
        'recipient_email': recipient_email,
        'recipient_name': recipient_name,
        'contract_content': contract_content,
    })

    
@login_required
def combined_contract_and_template_list(request):
    # Fetch search query from request
    search_query = request.GET.get('search', '')

    # Filter contracts based on search query
    contracts = Contract.objects.all().select_related('template', 'user').order_by('-created_at')
    if search_query:
        contracts = contracts.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__phone_number__icontains=search_query)  # Adjust field name for phone number
        )

    # Fetch templates
    templates = ContractTemplate.objects.all().order_by('-id')

    # Pagination for contracts (15 per page)
    contract_paginator = Paginator(contracts, 300)
    contract_page_number = request.GET.get('contract_page')
    contract_page = contract_paginator.get_page(contract_page_number)

    # Pagination for templates (8 per page)
    template_paginator = Paginator(templates, 8)
    template_page_number = request.GET.get('template_page')
    template_page = template_paginator.get_page(template_page_number)

    # Render response
    return render(request, 'contract_management/template_list.html', {
        'contracts': contract_page,
        'templates': template_page,
        'search_query': search_query,
    })


# Bulk upload contracts 
from django.db import transaction 
import magic  # Import the magic module to check file types

@login_required
def bulk_upload_contracts(request, template_id):
    contract_templates = ContractTemplate.objects.all()
    template = None

    if request.method == "POST":
        # Ensure that a file is uploaded
        if 'file' not in request.FILES:
            messages.error(request, "No file was uploaded.")
            return redirect('hrms:bulk_upload_contracts', template_id=template_id)

        excel_file = request.FILES['file']

        try:
            # Check the file extension
            if not excel_file.name.endswith(('.xlsx', '.xlsm')):
                raise ValidationError("The file must be in .xlsx or .xlsm format.")

            # Save the Excel file to a temporary location
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in excel_file.chunks():
                    temp_file.write(chunk)

            # Use pandas to read the Excel file
            try:
                df = pd.read_excel(temp_file.name, engine='openpyxl')
            except Exception as e:
                messages.error(request, f"Error reading the Excel file: {str(e)}")
                return redirect('hrms:bulk_upload_contracts', template_id=template_id)

            # Get headers from the first row
            headers = df.columns.tolist()

            # Get the template and placeholders
            template = ContractTemplate.objects.get(id=template_id)
            placeholders = Placeholder.objects.filter(id__in=template.placeholders.values_list('id', flat=True))

            # Ensure the Excel file contains required columns
            required_headers = ['email'] + [placeholder.key for placeholder in placeholders]

            if not all(header in headers for header in required_headers):
                messages.error(request, f"Excel file must include the following columns: {', '.join(required_headers)}")
                return redirect('hrms:bulk_upload_contracts', template_id=template_id)

            # Process each row in the Excel file and populate the contract content with placeholders
            contracts_to_review = []
            failed_emails = []
            with transaction.atomic():  # Use a transaction to ensure atomic updates
                for _, row in df.iterrows():
                    row_data = row.to_dict()
                    email = row_data.get('email')

                    if not email:
                        continue

                    try:
                        # Fetch the user by email
                        user = User.objects.get(email=email)
                        contract_content = template.template_content

                        # Replace placeholders in the template with Excel data
                        for placeholder in placeholders:
                            placeholder_value = row_data.get(placeholder.key, '')
                        
                            if placeholder_value:
                                contract_content = contract_content.replace(f"{{{{{placeholder.key}}}}}", placeholder_value)
                            else:
                                contract_content = contract_content.replace(f"{{{{{placeholder.key}}}}}", "N/A")

                        # Store the contract in the session for review
                        contracts_to_review.append({
                            'user_id': user.id,
                            'content': contract_content,
                            'email': email
                        })

                    except User.DoesNotExist:
                        failed_emails.append(email)

            # Store the contracts in session for later use
            request.session['contracts_to_review'] = contracts_to_review

            # Provide feedback to the user
            if contracts_to_review:
                messages.success(request, f"Contracts have been populated. Please review them before finalizing.")
            if failed_emails:
                messages.error(request, f"The following emails do not exist in the system: {', '.join(failed_emails)}")

            return redirect('hrms:preview_bulk_contract', template_id=template.id)

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('hrms:bulk_upload_contracts', template_id=template_id)
        except Exception as e:
            messages.error(request, f"An error occurred while processing the file: {str(e)}")
            return redirect('hrms:bulk_upload_contracts', template_id=template_id)

    try:
        template = ContractTemplate.objects.get(id=template_id)  # Fetch the template for GET requests
    except ContractTemplate.DoesNotExist:
        messages.error(request, "The selected contract template does not exist.")
        return redirect('hrms:bulk_upload_contracts_list')  # Adjust the redirect if needed

    return render(request, 'contract_management/bulk_upload.html', {'template': template})

@login_required
def preview_bulk_contract(request, template_id):
    try:
        # Fetch the contract template by ID
        template = ContractTemplate.objects.get(id=template_id)
    except ContractTemplate.DoesNotExist:
        raise Http404("Contract template not found.")
    
    # Handle form submission (POST)
    if request.method == "POST":
        try:
            # Get contract content and user ID from the POST request
            contract_content = request.POST.get('contract_content')
            user_id = request.POST.get('user_id')

            # Find the user based on the user_id
            user = User.objects.get(id=user_id)
            
            # Create the contract
            contract = Contract.objects.create(
                user=user,
                template=template,
                content=contract_content
            )

            # Prepare the contract review URL
            contract_review_url = request.build_absolute_uri(reverse('hrms:contract_preview', args=[contract.id]))

            # Prepare email content
            recipient_name = user.get_full_name().strip() or user.username
            html_message = render_to_string('contract_management/emails/contract_notification.html', {
                'recipient_name': recipient_name,
                'contract_id': contract.id,
                'contract_link': contract_review_url,
            })
            
            plain_message = f"""
                Hello {recipient_name},

                You have a pending contract to review and sign.

                Contract ID: {contract.id}
                Please visit the following link to review and sign the contract:
                {contract_review_url}

                Best regards,
            """
            
            # Send the email
            send_mail(
                "Contract Pending Review",
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message
            )

            # Mark the contract as email sent
            contract.email_sent = True
            contract.save()

            # Success message
            messages.success(request, "Contract successfully created and email sent.")
        
        except Exception as e:
            messages.error(request, f"Error occurred while creating the contract or sending email: {str(e)}")
            return redirect('hrms:preview_bulk_contract', template_id=template_id)  # Redirect back to the contract preview

        # Redirect to the template list or another suitable page after successful contract creation
        return redirect('hrms:bulk_upload_contracts', template_id=template_id)  

    # If it's a GET request, prepare the contract content with placeholders
    contract_data = {
        'full_name': "Default Name",  # Example of dynamic values; replace with actual user or related model data
        'id_number': '0000000',
        'phone_number': '0712111111',
        'employee_name': 'Mary Jhones',
        'employer_name': 'Jawabu Best Limited',
        'client_name': 'Client XYZ',
        'start_date': 'December 31, 2024',
        'end_date': 'December 31, 2025',
        'position': 'Software Developer',
        'salary': '$50,000 per year',
        'contract_type': 'Full-time',
        'department': 'IT Department',
        'supervisor': 'Jane Doe',
        'address': '123 Main St, City, Country',
        'project_name': 'Project X',
        'payment_terms': 'Monthly payments',
        'deliverables': 'Complete project by end of 2024',
        'working_hours': '9 AM - 5 PM',
        'agreement_date': 'December 31, 2024',
        'termination_clause': 'Either party can terminate with 30 days notice.',
    }

    # Use the render_template method to replace placeholders dynamically
    rendered_content = template.render_template(contract_data)

    # Render the preview page with the populated contract content
    return render(request, 'contract_management/preview_bulk_contract.html', {
        'template': template,
        'contract_content': rendered_content,
    })

# Sign contract (using jsignature)

@login_required
def sign_contract(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)

    if request.method == "POST":
        # Get the form data
        signature_data = request.POST.get('signature_data')
        initials = request.POST.get('initials')  # Make sure this is being received
        agree_to_contract = request.POST.get('agree_to_contract')

        # Ensure user agrees to the terms
        if not agree_to_contract:
            messages.error(request, "You must agree to the terms of the contract.")
            return redirect('hrms:sign_contract', contract_id=contract_id)

        # Validate that only one of signature or initials is provided

        if signature_data and initials:
            messages.error(request, "You can either draw your signature or enter your initials, but not both.")
            return redirect('hrms:sign_contract', contract_id=contract_id)

        # Save signature or initials based on the user input
        if signature_data:
            contract.signature = signature_data
        elif initials:
            contract.initials = initials  # Ensure this is saved when initials are provided

        # Set the signing status based on user role
        if request.user.is_superuser or request.user.is_staff or hasattr(request.user, 'role') and request.user.role == 'human_resource_manager':
            contract.admin_signed = True
        else:
            contract.user_signed = True

        contract.save()  # Save the contract with the updated signature/initials

        # Redirect to success page
        messages.success(request, "You have successfully signed the contract.")
        return redirect('hrms:contract_sign_success', contract_id=contract_id)

    return render(request, 'contract_management/sign_contract.html', {'contract': contract})


@login_required
def contract_sign_success(request, contract_id):
    """
    Success page displayed after the contract is successfully signed.
    """
    contract = get_object_or_404(Contract, pk=contract_id)
    return render(request, 'contract_management/contract_sign_success.html', {'contract': contract})

def privacy_policy(request):
    return render(request, 'contract_management/privacy_policy.html')


# TROUBLE SHOOT
@login_required
def upload_contract_excel(request):
    if request.method == 'POST' and request.FILES.get('file'):
        excel_file = request.FILES['file']
        data = pd.read_excel(excel_file)
        return JsonResponse({'columns': list(data.columns)}, status=200)

    return render(request, 'contract_management/upload_excel.html')

def replace_placeholders(template_content, data_row):
    for key, value in data_row.items():
        template_content = template_content.replace(f'{{{{ {key} }}}}', str(value))
    return template_content

def generate_contracts(request):
    if request.method == 'POST':
        template_id = request.POST['template_id']
        excel_file = request.FILES.get('file')

        if not excel_file:
            messages.error(request, "Please upload a file.")
            return redirect('generate_contracts')

        if not excel_file.name.endswith(('.xls', '.xlsx')):
            messages.error(request, "Invalid file format. Please upload an Excel file.")
            return redirect('generate_contracts')

        # Fetch the selected template
        try:
            template = ContractTemplate.objects.get(id=template_id)
        except ContractTemplate.DoesNotExist:
            messages.error(request, "Selected template does not exist.")
            return redirect('generate_contracts')

        # Handle temporary file saving
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', excel_file.name)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)  # Ensure temp directory exists
        try:
            with open(temp_path, 'wb+') as temp_file:
                for chunk in excel_file.chunks():
                    temp_file.write(chunk)

            # Read Excel data
            data = pd.read_excel(temp_path).to_dict(orient='records')

        except Exception as e:
            messages.error(request, f"Error reading file: {str(e)}")
            return redirect('generate_contracts')

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)  # Clean up temporary file

        # Validate and generate contracts
        contracts = []
        for row in data:
            try:
                # Check for missing keys
                missing_keys = [
                    placeholder.key for placeholder in template.placeholders.all()
                    if placeholder.key not in row
                ]
                if missing_keys:
                    messages.warning(request, f"Missing placeholders {missing_keys} in row {row}")
                    continue

                # Render template
                jinja_template = Template(template.template_content)
                filled_content = jinja_template.render(row)

                # Create contract
                contracts.append(Contract(content=filled_content, template=template, user=request.user))

            except Exception as e:
                messages.warning(request, f"Error processing row {row}: {str(e)}")
                continue

        # Bulk save contracts
        if contracts:
            Contract.objects.bulk_create(contracts)
            messages.success(request, f"{len(contracts)} contracts generated successfully!")
        else:
            messages.warning(request, "No contracts were generated due to errors.")
        return redirect('hrms:template_list')

    templates = ContractTemplate.objects.all()
    return render(request, 'contract_management/generate_bulk_contracts.html', {'templates': templates})

from .forms import ContractTemplateForm

@login_required
def create_bulk_contract_template(request):
    if request.method == 'POST':
        form = ContractTemplateForm(request.POST)
        if form.is_valid(): 
            form.save()
            messages.success(request, "Contract template created successfully.")
            return redirect('hrms:create_contract_template')  # Redirect to the same page or a list view
        else:
            messages.error(request, "There was an error creating the template.")
    else:
        form = ContractTemplateForm()

    return render(request, 'contract_management/create_bulk_template.html', {'form': form})