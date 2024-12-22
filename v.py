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
from jsignature.utils import draw_signature
import base64
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image
from reportlab.pdfgen import canvas

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
        placeholder_values = {}

        # Make sure placeholder values are valid and not empty
        for placeholder in template.placeholders.all():
            key = placeholder.key
            value = request.POST.get(key, f"[{placeholder.name}]")

            # Only add to the dictionary if key and value are not empty
            if key and value:
                placeholder_values[key] = value

        if placeholder_values:
            # Render the template content with the filled placeholders
            template_content = Template(template.template_content)
            context = Context(placeholder_values)
            filled_contract = template_content.render(context)

            # Create the contract with the filled content
            contract = Contract.objects.create(template=template, content=filled_contract)

            return redirect('hrms:contract_preview', contract_id=contract.id)
        else:
            # In case no valid placeholders were filled
            messages.error(request, "No valid placeholder values provided.")

    return render(request, 'contract_management/contract_preview.html', {'template': template})


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

        # Add title
        pdf_canvas.setFont("Helvetica-Bold", 14)
        pdf_canvas.drawString(100, 800, f"Contract Preview - {contract.user.get_full_name() if contract.user else 'N/A'}")

        # Add contract content dynamically
        pdf_canvas.setFont("Helvetica", 12)
        lines = contract_content.split('\n')  # Split content into lines
        y_position = 780  # Start position for content

        for line in lines:
            pdf_canvas.drawString(100, y_position, line)
            y_position -= 15  # Adjust line height
            if y_position < 50:  # Handle page overflow
                pdf_canvas.showPage()
                y_position = 800  # Reset for the next page

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

import base64
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
from .models import Contract
from io import BytesIO
from PIL import Image

def base64_to_image(base64_data):
    """Converts a base64 string to an image ContentFile."""
    if not base64_data:
        return None

    try:
        # Decode the base64 data
        image_data = base64.b64decode(base64_data)
        image = Image.open(BytesIO(image_data))

        # Force the image format to PNG (default)
        image_format = image.format if image.format else 'PNG'
        buffer = BytesIO()
        image.save(buffer, format=image_format)

        # Create a ContentFile object
        return ContentFile(buffer.getvalue(), name=f"signature.{image_format.lower()}")
    except Exception as e:
        print(f"Error decoding image: {e}")
        return None

@login_required
def sign_contract(request, contract_id):
    """
    Handles the contract signing process, allowing users to draw/sign their signature
    and provide initials.
    """
    contract = get_object_or_404(Contract, pk=contract_id)

    if request.method == "POST":
        # Get form data
        signature_data = request.POST.get('signature_data')  # Base64 encoded signature
        initials = request.POST.get('initials', '').strip()  # Strip spaces from initials

        # Validate if signature or initials are provided
        if not signature_data and not initials:
            messages.error(request, "Please provide a signature or initials before submitting.")
            return render(request, 'contract_management/sign_contract.html', {'contract': contract})

        # Handle signature saving
        if signature_data:
            try:
                # Convert base64 data to an image file
                signature_image = base64_to_image(signature_data)

                if signature_image:
                    # Check user role and save appropriate signature
                    if request.user.role == 'employee':
                        # Remove existing signature before saving new one
                        if contract.user_signature:
                            contract.user_signature.delete(save=False)
                        contract.user_signature.save(f"user_signature_{contract.id}.png", signature_image, save=False)
                        contract.user_signed = True  # Mark user as signed
                    elif request.user.role in ['human_resource_manager'] or request.user.is_superuser:
                        if contract.admin_signature:
                            contract.admin_signature.delete(save=False)
                        contract.admin_signature.save(f"admin_signature_{contract.id}.png", signature_image, save=False)
                        contract.admin_signed = True  # Mark admin as signed
                else:
                    messages.error(request, "Invalid signature format. Please try again.")
                    return render(request, 'contract_management/sign_contract.html', {'contract': contract})

            except Exception as e:
                print(f"Error saving signature: {e}")
                messages.error(request, "Failed to save the signature. Please try again.")
                return render(request, 'contract_management/sign_contract.html', {'contract': contract})

        # Handle initials saving
        if initials:
            try:
                if request.user.role == 'employee':
                    contract.user_initials = initials
                    contract.user_signed = True  # Ensure consistency
                elif request.user.role in ['human_resource_manager'] or request.user.is_superuser:
                    contract.admin_initials = initials
                    contract.admin_signed = True  # Ensure consistency
            except Exception as e:
                print(f"Error saving initials: {e}")
                messages.error(request, "Failed to save initials. Please try again.")
                return render(request, 'contract_management/sign_contract.html', {'contract': contract})

        # Save contract updates
        try:
            contract.save()
            messages.success(request, "You have successfully signed the contract.")
        except Exception as e:
            print(f"Error saving contract: {e}")
            messages.error(request, "An error occurred while saving the contract. Please try again.")

        # Check if both parties have signed
        if contract.user_signed and contract.admin_signed:
            # Generate and send the signed contract PDF
            send_signed_contract_pdf(contract)

        # No need to redirect, just re-render with success message
        return render(request, 'contract_management/sign_contract.html', {'contract': contract})

    # Render the signing form if it's a GET request
    return render(request, 'contract_management/sign_contract.html', {'contract': contract})

def send_signed_contract_pdf(contract):
    """
    Sends the signed contract PDF to the user once both parties have signed.
    """
    try:
        # Generate the signed contract PDF
        pdf = generate_signed_contract_pdf(contract)

        # Email the signed contract PDF
        send_mail(
            subject="Contract Signature Complete",
            message="Your contract has been signed by both parties. Please find the signed contract attached.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contract.user.email],
            fail_silently=False,
            html_message="Your contract has been signed by both parties. Please find the signed contract attached.",
            attachments=[(
                f"contract_{contract.id}_signed.pdf",
                pdf,
                'application/pdf'
            )]
        )
        messages.success(request, "Signed contract PDF sent successfully.")
    except Exception as e:
        print(f"Error sending signed contract PDF: {e}")
        messages.error(request, "Failed to send the signed contract PDF. Please try again.")


@login_required
def view_signed_contract(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    signature_image = get_signature_image(contract.signature)
    return render(request, 'contract_management/view_contract.html', {
        'contract': contract,
        'signature_image': signature_image,
    })

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

from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML
from django.contrib.staticfiles import finders

from django.conf import settings

def generate_contract_pdf(request, contract_id):
    # Retrieve the contract from the database based on the contract_id
    try:
        contract = Contract.objects.get(id=contract_id)
    except Contract.DoesNotExist:
        return HttpResponse("Contract not found", status=404)

    # Render the HTML template with context
    template = get_template('contract_management/pdf/download-contract.html')  # Adjust the path to your template
    context = {'contract': contract}
    html_content = template.render(context)

    # Get the logo URL from settings or hardcode it (better for flexibility)
    logo_url = getattr(settings, 'LOGO_URL', 'https://www.jawabubest-wms.com/static/hrms/images/logo.png')

    # Modify the HTML content to use the full URL for the logo
    html_content = html_content.replace('{% static "hrms/images/logo.png" %}', logo_url)

    # Generate PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="contract_{contract_id}.pdf"'

    try:
        # Use WeasyPrint to generate the PDF
        HTML(string=html_content).write_pdf(response)
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

    return response

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
from jsignature.utils import draw_signature
import base64
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image
from reportlab.pdfgen import canvas
from .forms import ContractTemplateForm

# Bulk upload contracts 
from django.db import transaction 
import magic  # Import the magic module to check file types

import base64
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
from .models import Contract
from io import BytesIO
from PIL import Image

from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML
from django.contrib.staticfiles import finders

from django.conf import settings

from hrms.models import AccountManager, Employee, HumanResourceManager

# User Search for Contract Signatories
import logging
logger = logging.getLogger(__name__)

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
    # Fetch the template using the provided template_id
    template = get_object_or_404(ContractTemplate, pk=template_id)

    # Handle POST request to create a contract
    if request.method == 'POST':
        placeholder_values = {}
        placeholders = template.placeholders.all()

        # Check if the template has placeholders
        if not placeholders:
            messages.error(request, "This template does not have any placeholders.")
            # Create contract without placeholders if needed
            contract = Contract.objects.create(template=template, content=template.template_content)
            return redirect('hrms:contract_preview', contract_id=contract.id)

        # Ensure the placeholder values are valid and not empty
        for placeholder in placeholders:
            key = placeholder.key
            value = request.POST.get(key, None)  # Get the value for the placeholder
            
            # Add to dictionary only if the value is not empty
            if value:
                placeholder_values[key] = value
            else:
                # If any placeholder is left empty, show an error
                messages.error(request, f"Please fill in the placeholder: {placeholder.name}")

        # If all placeholders have been filled
        if placeholder_values:
            # Render the template content with the filled placeholders
            template_content = Template(template.template_content)
            context = Context(placeholder_values)
            filled_contract = template_content.render(context)

            # Create the contract with the filled content
            contract = Contract.objects.create(template=template, content=filled_contract)

            # Debug to verify contract creation
            print(f"Created contract ID: {contract.id}")

            # Redirect to the contract preview page with valid contract_id
            return redirect('hrms:contract_preview', contract_id=contract.id)
        else:
            # In case no valid placeholder values were provided
            messages.error(request, "No valid placeholder values provided.")
    
    # Render the form for the contract creation (pass the template data)
    return render(request, 'contract_management/create_contract.html', {
        'template': template
    })

@login_required
def contract_preview(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    contract_template = contract.template
    placeholders = contract_template.placeholders.all()

    recipient_email = None
    recipient_name = None

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
                    'contract_content': contract_content,
                    'success': True,
                    'recipient_name': recipient_name,
                    'recipient_email': recipient_email,
                })
            except User.DoesNotExist:
                messages.error(request, "User with the provided email does not exist.")
        else:
            messages.error(request, "Recipient email is required.")

    # Handle PDF generation
    if request.GET.get('generate_pdf'):
        buffer = BytesIO()
        pdf_canvas = canvas.Canvas(buffer)

        # Add title
        pdf_canvas.setFont("Helvetica-Bold", 14)
        pdf_canvas.drawString(100, 800, f"Contract Preview - {contract.user.get_full_name() if contract.user else 'N/A'}")

        # Add contract content dynamically
        pdf_canvas.setFont("Helvetica", 12)
        lines = contract_content.split('\n')  # Split content into lines
        y_position = 780  # Start position for content

        for line in lines:
            pdf_canvas.drawString(100, y_position, line)
            y_position -= 15  # Adjust line height
            if y_position < 50:  # Handle page overflow
                pdf_canvas.showPage()
                y_position = 800  # Reset for the next page

        pdf_canvas.showPage()
        pdf_canvas.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=contract_{contract.id}.pdf'
        return response

    # Render the preview page
    return render(request, 'contract_management/contract_preview.html', {
        'contract': contract,
        'contract_content': contract_content,
        'email_sent': contract.email_sent,
        'recipient_email': recipient_email,
        'recipient_name': recipient_name,
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

@login_required
def bulk_upload_contracts(request, template_id):
    # Get all contract templates for display
    contract_templates = ContractTemplate.objects.all()

    if request.method == "POST":
        # Ensure a file is uploaded
        if 'file' not in request.FILES:
            messages.error(request, "No file was uploaded.")
            return redirect('hrms:bulk_upload_contracts', template_id=template_id)

        excel_file = request.FILES['file']  

        try:
            # Validate file extension
            if not excel_file.name.endswith(('.xlsx', '.xlsm')):
                raise ValidationError("The file must be in .xlsx or .xlsm format.")

            # Save the Excel file to a temporary location
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in excel_file.chunks():
                    temp_file.write(chunk)

            # Read the Excel file using pandas
            try:
                df = pd.read_excel(temp_file.name, engine='openpyxl')
            except Exception as e:
                messages.error(request, f"Error reading the Excel file: {str(e)}")
                return redirect('hrms:bulk_upload_contracts', template_id=template_id)

            # Validate the required columns
            template = get_object_or_404(ContractTemplate, id=template_id)
            placeholders = Placeholder.objects.filter(id__in=template.placeholders.values_list('id', flat=True))
            required_headers = ['email'] + [placeholder.key for placeholder in placeholders]

            if not all(header in df.columns for header in required_headers):
                missing_columns = [header for header in required_headers if header not in df.columns]
                messages.error(request, f"Excel file is missing required columns: {', '.join(missing_columns)}")
                return redirect('hrms:bulk_upload_contracts', template_id=template_id)

            # Process the rows to populate contracts
            contracts_to_review = []
            failed_emails = []

            with transaction.atomic():  # Ensure atomicity
                for _, row in df.iterrows():
                    row_data = row.to_dict()
                    email = row_data.get('email')

                    if not email:
                        continue  # Skip rows without email

                    try:
                        # Fetch the user by email
                        user = User.objects.get(email=email)
                        contract_content = template.template_content

                        # Replace placeholders with data from Excel
                        for placeholder in placeholders:
                            value = row_data.get(placeholder.key, 'N/A')
                            contract_content = contract_content.replace(f"{{{{{placeholder.key}}}}}", str(value))

                        # Append the contract for review
                        contracts_to_review.append({
                            'user_id': user.id,
                            'content': contract_content,
                            'email': email
                        })

                    except User.DoesNotExist:
                        failed_emails.append(email)

            # Store contracts for review in session
            request.session['contracts_to_review'] = contracts_to_review

            # Provide feedback
            if contracts_to_review:
                messages.success(request, "Contracts populated successfully. Please review them before finalizing.")
            if failed_emails:
                messages.warning(request, f"The following emails do not exist in the system: {', '.join(failed_emails)}")

            return redirect('hrms:preview_bulk_contract', template_id=template_id)

        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
        finally:
            if 'temp_file' in locals() and temp_file:
                # Ensure the temporary file is deleted
                temp_file.close()

        return redirect('hrms:bulk_upload_contracts', template_id=template_id)

    # For GET requests, fetch the template and render the form
    template = get_object_or_404(ContractTemplate, id=template_id)
    return render(request, 'contract_management/bulk_upload.html', {
        'template': template,
        'contract_templates': contract_templates
    })



@login_required
def preview_bulk_contract(request, template_id):
    try:
        # Fetch the contract template by ID
        template = get_object_or_404(ContractTemplate, id=template_id)
    except Http404:
        messages.error(request, "Contract template not found.")
        return redirect('hrms:template_list')

    if request.method == "POST":
        try:
            # Handle form submission for bulk contracts
            contract_content = request.POST.get('contract_content')
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)

            # Create the contract
            contract = Contract.objects.create(
                user=user,
                template=template,
                content=contract_content
            )

            # Prepare the contract review URL
            contract_review_url = request.build_absolute_uri(reverse('hrms:contract_preview', args=[contract.id]))

            # Prepare email content
            recipient_name = user.get_full_name() or user.username
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
                HRMS Team
            """

            # Send the email
            send_mail(
                subject="Contract Pending Review",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
            )

            # Mark the contract as email sent
            contract.email_sent = True
            contract.save()

            messages.success(request, f"Contract for {recipient_name} successfully sent.")
        
        except Exception as e:
            messages.error(request, f"Error occurred: {str(e)}")
            return redirect('hrms:preview_bulk_contract', template_id=template_id)

        # Redirect to the list of sent contracts
        return redirect('hrms:template_list')

    # For GET requests, preview the bulk contract with placeholders
    contract_data = {
        'full_name': "Default Name",
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

    # Render the contract with placeholders replaced
    rendered_content = template.render_template(contract_data)

    # Fetch all sent contracts for the template
    sent_contracts = Contract.objects.filter(template=template)

    return render(request, 'contract_management/preview_bulk_contract.html', {
        'template': template,
        'contract_content': rendered_content,
        'sent_contracts': sent_contracts,
    })
# Sign contract (using jsignature)

def send_signed_contract_pdf(contract):
    """
    Sends the signed contract PDF to the user once both parties have signed.
    """
    try:
        # Generate the signed contract PDF
        pdf = generate_signed_contract_pdf(contract)

        # Email the signed contract PDF
        send_mail(
            subject="Contract Signature Complete",
            message="Your contract has been signed by both parties. Please find the signed contract attached.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contract.user.email],
            fail_silently=False,
            html_message="Your contract has been signed by both parties. Please find the signed contract attached.",
            attachments=[(
                f"contract_{contract.id}_signed.pdf",
                pdf,
                'application/pdf'
            )]
        )
        messages.success(request, "Signed contract PDF sent successfully.")
    except Exception as e:
        print(f"Error sending signed contract PDF: {e}")
        messages.error(request, "Failed to send the signed contract PDF. Please try again.")

@login_required
def contract_sign_success(request, contract_id):
    """
    Success page displayed after the contract is successfully signed.
    """
    contract = get_object_or_404(Contract, pk=contract_id)
    return render(request, 'contract_management/contract_sign_success.html', {'contract': contract})

def base64_to_image(base64_data):
    """Converts a base64 string to an image ContentFile."""
    if not base64_data:
        return None

    # Ensure the data is clean (strip the prefix if present)
    if base64_data.startswith("data:image"):
        base64_data = base64_data.split(",")[1]  # Remove the metadata prefix

    try:
        # Decode the base64 data
        image_data = base64.b64decode(base64_data)
        image = Image.open(BytesIO(image_data))

        # Force the image format to PNG (default)
        image_format = image.format if image.format else 'PNG'
        buffer = BytesIO()
        image.save(buffer, format=image_format)

        # Create a ContentFile object
        return ContentFile(buffer.getvalue(), name=f"signature.{image_format.lower()}")
    except Exception as e:
        logger.error(f"Error decoding image: {e}")
        return None


@login_required
def sign_contract(request, contract_id):
    """
    Handles the contract signing process, allowing users (employee/admin) to draw/sign their signature
    or provide initials individually.
    """
    logger.info("User %s is attempting to sign contract ID %d", request.user.username, contract_id)
    contract = get_object_or_404(Contract, pk=contract_id)

    if request.method == "POST":
        logger.debug("Processing POST request for contract ID %d", contract_id)

        # Get form data
        signature_data = request.POST.get('signature_data')  # Base64 encoded signature
        initials = request.POST.get('initials', '').strip()  # Strip spaces from initials

        if signature_data and "data:image" in signature_data:
            try:
                logger.debug("Attempting to save signature for user %s", request.user.username)
                signature_image = base64_to_image(signature_data)

                if signature_image:
                    if request.user.role == 'employee':
                        contract.user_signature = signature_image
                        contract.user_signed = True
                        logger.info("User %s signed contract ID %d as employee", request.user.username, contract_id)
                    elif request.user.role in ['human_resource_manager', 'superuser']:
                        contract.admin_signature = signature_image
                        contract.admin_signed = True
                        logger.info("User %s signed contract ID %d as admin", request.user.username, contract_id)
                else:
                    messages.error(request, "Invalid signature format. Please try again.")
                    logger.error("Invalid signature format for user %s", request.user.username)
                    return render(request, 'contract_management/sign_contract.html', {'contract': contract})
            except Exception as e:
                logger.exception("Error saving signature for user %s: %s", request.user.username, str(e))
                messages.error(request, "Failed to save the signature. Please try again.")
                return render(request, 'contract_management/sign_contract.html', {'contract': contract})

        elif initials:
            try:
                logger.debug("Attempting to save initials for user %s", request.user.username)
                if request.user.role == 'employee':
                    contract.user_initials = initials
                    contract.user_signed = True
                elif request.user.role in ['human_resource_manager', 'superuser']:
                    contract.admin_initials = initials
                    contract.admin_signed = True
                logger.info("Initials saved for user %s on contract ID %d", request.user.username, contract_id)
            except Exception as e:
                logger.exception("Error saving initials for user %s: %s", request.user.username, str(e))
                messages.error(request, "Failed to save initials. Please try again.")
                return render(request, 'contract_management/sign_contract.html', {'contract': contract})
        
        # Save contract updates after signature or initials are saved
        try:
            contract.save()
            logger.info("Contract ID %d saved successfully after signing by user %s", contract_id, request.user.username)
            messages.success(request, "You have successfully signed the contract.")
        except Exception as e:
            logger.exception("Error saving contract ID %d: %s", contract_id, str(e))
            messages.error(request, "An error occurred while saving the contract. Please try again.")

        return redirect('hrms:contract_sign_success', contract_id=contract.id)

    return render(request, 'contract_management/sign_contract.html', {'contract': contract})

def privacy_policy(request):
    return render(request, 'contract_management/privacy_policy.html')

def generate_contract_pdf(request, contract_id):
    # Retrieve the contract from the database based on the contract_id
    try:
        contract = Contract.objects.get(id=contract_id)
    except Contract.DoesNotExist:
        return HttpResponse("Contract not found", status=404)

    # Render the HTML template with context
    template = get_template('contract_management/pdf/download-contract.html')  # Adjust the path to your template
    context = {'contract': contract}
    html_content = template.render(context)

    # Get the logo URL from settings or hardcode it (better for flexibility)
    logo_url = getattr(settings, 'LOGO_URL', 'https://www.jawabubest-wms.com/static/hrms/images/logo.png')

    # Modify the HTML content to use the full URL for the logo
    html_content = html_content.replace('{% static "hrms/images/logo.png" %}', logo_url)

    # Generate PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="contract_{contract_id}.pdf"'

    try:
        # Use WeasyPrint to generate the PDF
        HTML(string=html_content).write_pdf(response)
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

    return response

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

# Memo
from .forms import MemoForm
from .models import Memo
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

@login_required
def filter_users(request):
    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '')

    # Query the models based on the selected role
    if role_filter == 'account_manager':
        users = AccountManager.objects.filter(user__username__icontains=search_query).values('user__id', 'user__first_name', 'user__last_name')
    elif role_filter == 'employee':
        users = Employee.objects.filter(user__username__icontains=search_query).values('user__id', 'user__first_name', 'user__last_name')
    elif role_filter == 'human_resource_manager':
        users = HumanResourceManager.objects.filter(user__username__icontains=search_query).values('user__id', 'user__first_name', 'user__last_name')
    elif role_filter == 'all':
        users = User.objects.filter(username__icontains=search_query).values('id', 'first_name', 'last_name')
    else:
        users = []  # Return empty list if role is unrecognized

    # Return users in JSON format
    user_list = list(users)
    return JsonResponse(user_list, safe=False)


@login_required
def create_memo(request):
    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '')

    # Consolidate role filtering
    roles = {
        'account_manager': User.ACCOUNT_MANAGER,
        'employee': User.EMPLOYEE,
        'human_resource_manager': User.HUMAN_RESOURCE_MANAGER,
    }
    users = User.objects.filter(email__icontains=search_query)
    if role_filter in roles:
        users = users.filter(role=roles[role_filter])

    if request.method == "POST":
        form = MemoForm(request.POST)
        if form.is_valid():
            memo = form.save(commit=False)
            memo.sender = request.user
            memo.save()

            # Prepare email content
            subject = f"New Memo from {request.user.first_name} {request.user.last_name}"
            html_content = render_to_string('contract_management/emails/memo_email.html', {
                'sender': request.user,
                'memo': memo,
            })
            text_content = strip_tags(html_content)

            # Determine recipients
            role_categories = {
                'all': [User.ACCOUNT_MANAGER, User.EMPLOYEE, User.HUMAN_RESOURCE_MANAGER],
                'employee': [User.EMPLOYEE],
                'account_manager': [User.ACCOUNT_MANAGER],
                'human_resource_manager': [User.HUMAN_RESOURCE_MANAGER],
            }
            recipients = User.objects.filter(
                role__in=role_categories.get(memo.recipients_category, [])
            ).values_list('email', flat=True)

            # Send emails with exception handling
            try:
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=request.user.email,
                    to=list(recipients),
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                messages.success(request, "Memo sent successfully and emails have been delivered!")
            except Exception as e:
                messages.error(request, f"Failed to send emails: {str(e)}")

            return redirect('hrms:list_memo')
        else:
            messages.error(request, "There was an error with the form. Please try again.")

    else:
        form = MemoForm()

    return render(request, 'contract_management/memo/create_memo.html', {
        'form': form,
        'users': users,
        'role_filter': role_filter,
        'search_query': search_query,
    })
    
@login_required
def list_memo(request):
    user = request.user
    sent_memos = Memo.objects.filter(sender=user).order_by('-created_at')
    received_memos = Memo.objects.filter(recipients_category=user).order_by('-created_at')

    context = {
        'sent_memos': sent_memos,
        'received_memos': received_memos,
    }
    return render(request, 'contract_management/memo/memo_list.html', context)
