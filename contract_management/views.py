from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from contract_management.models import ContractTemplate, Placeholder, Contract
from hrms.models import User
from django.template import Template, Context
from django.http import JsonResponse
from .forms import ContractSignatureForm
from jsignature.forms import JSignatureField
import csv
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.contrib import messages
import openpyxl
from openpyxl import load_workbook  # <-- Add this import
from .forms import ExcelUploadForm
import pandas as pd

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
def contract_preview(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    contract_templates = ContractTemplate.objects.all()

    email_sent = contract.email_sent  # Get the email_sent status from the model
    recipient_email = None
    recipient_name = None

    # Get the placeholders from the contract template
    contract_template = contract.template
    placeholders = contract_template.placeholders.all()

    # Prepare dynamic data for placeholders (example fields from the Contract and User models)
    contract_data = {
        'full_name': contract.user.get_full_name(),  # Assuming this method exists
        'id_number': contract.user.id_number,  # Assuming id_number is a field in the User model
        'phone_number': contract.user.phone_number,  # Assuming phone_number is a field in the User model
        'employee_name': contract.user.get_full_name(),  # Same as full name
        'employer_name': 'Jawabu Best Limited',  # Assuming employer name is constant
        'client_name': 'Client XYZ',  # This could come from another related model
        'start_date': contract.created_at.strftime('%B %d, %Y'),
        'end_date': 'December 31, 2025',  # You can calculate or pass dynamically
        'position': 'Software Developer',  # Example static data or fetched dynamically
        'salary': '$50,000 per year',  # Example static data or fetched dynamically
        'contract_type': 'Full-time',  # Example static data or fetched dynamically
        'department': 'IT Department',  # Example static data or fetched dynamically
        'supervisor': 'Jane Doe',  # Example static data or fetched dynamically
        'address': '123 Main St, City, Country',  # Example static data or fetched dynamically
        'project_name': 'Project X',  # Example static data or fetched dynamically
        'payment_terms': 'Monthly payments',  # Example static data or fetched dynamically
        'deliverables': 'Complete project by end of 2024',  # Example static data or fetched dynamically
        'working_hours': '9 AM - 5 PM',  # Example static data or fetched dynamically
        'agreement_date': contract.created_at.strftime('%B %d, %Y'),
        'termination_clause': 'Either party can terminate with 30 days notice.',  # Example static data
    }

    # Replace the placeholders in the contract template content with actual data
    contract_content = contract_template.template_content

    for placeholder in placeholders:
        placeholder_key = placeholder.key
        if placeholder_key in contract_data:
            # Replace the placeholder with the actual value
            contract_content = contract_content.replace(f'{{{{ {placeholder_key} }}}}', contract_data[placeholder_key])

    # Handle the form submission and email sending
    if request.method == 'POST':
        recipient_email = request.POST.get('recipient_email')
        if recipient_email:
            try:
                # Fetch the user with the given email
                user = User.objects.get(email=recipient_email)
                # Assign the user to the contract
                contract.user = user
                contract.save()

                # Generate contract review URL
                contract_review_url = request.build_absolute_uri(reverse('hrms:contract_preview', args=[contract.id]))
                subject = "Contract Notification"

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
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient_email],
                    html_message=html_message
                )

                # Mark the contract as email sent
                contract.email_sent = True
                contract.save()

                # Pass success message and relevant details to the template
                messages.success(request, f"Email sent successfully to {recipient_name} ({recipient_email}).")
                return render(request, 'contract_management/contract_preview.html', {
                    'contract': contract,
                    'contract_templates': contract_templates,
                    'success': True,
                    'recipient_name': recipient_name,
                    'recipient_email': recipient_email,
                    'contract_content': contract_content  # Include the updated contract content
                })

            except User.DoesNotExist:
                messages.error(request, "User with the provided email does not exist.")
                return render(request, 'contract_management/contract_preview.html', {
                    'contract': contract,
                    'contract_templates': contract_templates,
                    'success': False,
                    'contract_content': contract_content  # Include the updated contract content
                })

        messages.error(request, "Recipient email is required.")
        return render(request, 'contract_management/contract_preview.html', {
            'contract': contract,
            'contract_templates': contract_templates,
            'success': False,
            'contract_content': contract_content  # Include the updated contract content
        })

    # Ensure recipient_name is passed even if the form hasn't been submitted
    return render(request, 'contract_management/contract_preview.html', {
        'contract': contract,
        'contract_templates': contract_templates,
        'email_sent': email_sent,
        'recipient_email': recipient_email,
        'recipient_name': recipient_name,
        'contract_content': contract_content  # Include the updated contract content
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

    # Pagination for templates (5 per page)
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
            # Check if the uploaded file is an Excel file
            if not excel_file.name.endswith('.xlsx'):
                raise ValidationError("The file must be in .xlsx format.")

            # Load the Excel file
            workbook = load_workbook(excel_file)
            sheet = workbook.active  # Use the active sheet (first sheet)

            # Get the template and placeholders
            template = ContractTemplate.objects.get(id=template_id)
            placeholders = Placeholder.objects.filter(id__in=template.placeholders.values_list('id', flat=True))

            # Ensure the Excel file contains required columns
            headers = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
            required_headers = ['email'] + [placeholder.key for placeholder in placeholders]

            if not all(header in headers for header in required_headers):
                messages.error(request, f"Excel file must include the following columns: {', '.join(required_headers)}")
                return redirect('hrms:bulk_upload_contracts', template_id=template_id)

            # Process each row in the Excel file and populate the contract content with placeholders
            contracts_to_review = []
            failed_emails = []
            with transaction.atomic():  # Use a transaction to ensure atomic updates
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    row_data = dict(zip(headers, row))
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


from django.shortcuts import render
from django.contrib import messages
from .models import ContractTemplate, Placeholder, Contract
from django.http import Http404

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from .models import ContractTemplate, Placeholder, Contract, User
from django.http import Http404
from django.conf import settings

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
        return redirect('hrms:template_list')  

    # If it's a GET request, prepare the contract content with placeholders
    placeholders = Placeholder.objects.filter(id__in=template.placeholders.values_list('id', flat=True))

    contract_content = template.template_content
    # Replace placeholders with actual values (from GET request or default)
    for placeholder in placeholders:
        placeholder_value = request.GET.get(placeholder.key, "N/A")  # Default value as "N/A"
        contract_content = contract_content.replace(f"{{{{{placeholder.key}}}}}", placeholder_value)

    # Render the preview page with the populated contract content
    return render(request, 'contract_management/preview_bulk_contract.html', {
        'template': template,
        'contract_content': contract_content,
        'placeholders': placeholders,  # Pass placeholders for form display
    })

# new
from django.http import HttpResponseBadRequest


# def bulk_upload_contracts(request, template_id):
#     # Get the contract template based on the provided template ID
#     template = ContractTemplate.objects.get(id=template_id)
#     placeholders = template.placeholders.all()

#     # Check if placeholders exist
#     if not placeholders:
#         messages.warning(request, "No placeholders available for this template.")

#     if request.method == 'POST':
#         # Check if the 'excel_file' key exists in the request FILES
#         if 'excel_file' not in request.FILES:
#             return HttpResponseBadRequest('No Excel file uploaded.')

#         excel_file = request.FILES['excel_file']

#         try:
#             # Load the Excel file using openpyxl
#             workbook = openpyxl.load_workbook(excel_file)
#             sheet = workbook.active
#             rows = list(sheet.iter_rows(min_row=2, values_only=True))  # Skip header row

#             print(f"Rows in Excel: {rows}")  # Debugging line to check the rows

#             # Iterate through each row of data
#             for row in rows:
#                 if not any(row):  # Skip empty rows
#                     continue

#                 # Initialize contract content with the template content
#                 content = template.template_content

#                 # Replace placeholders in the template with the corresponding data from the Excel row
#                 for i, placeholder in enumerate(placeholders):
#                     placeholder_key = "{" + placeholder.key + "}"  # Use single curly braces for replacement
#                     if i < len(row):
#                         content = content.replace(placeholder_key, str(row[i]))

#                 # Create and save the contract
#                 contract = Contract(
#                     user=request.user,  # Assuming user is logged in
#                     template=template,
#                     content=content
#                 )
#                 contract.save()

#             # Success message after contract creation
#             messages.success(request, "Contracts generated successfully from the Excel data.")
#             return redirect('hrms:template_list')  # Redirect to the list of templates or contracts

#         except Exception as e:
#             # Handle any errors that occur during file processing
#             messages.error(request, f"Error reading the Excel file: {e}")
#             return redirect('hrms:bulk_upload_contracts_list')

#     return render(request, 'contract_management/bulk_upload.html', {'template': template, 'placeholders': placeholders})    

# Sign contract (using jsignature)

@login_required
def sign_contract(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)

    if request.method == "POST":
        # Get the form data
        signature_data = request.POST.get('signature_data')
        initials = request.POST.get('initials')
        agree_to_contract = request.POST.get('agree_to_contract')

        if not agree_to_contract:
            messages.error(request, "You must agree to the terms of the contract.")
            return redirect('hrms:sign_contract', contract_id=contract_id)

        if signature_data and initials:
            messages.error(request, "You can either draw your signature or enter your initials, but not both.")
            return redirect('hrms:sign_contract', contract_id=contract_id)

        if signature_data:
            contract.signature = signature_data
        if initials:
            contract.initials = initials

        if request.user.is_superuser or request.user.is_staff or hasattr(request.user, 'role') and request.user.role == 'human_resource_manager':
            contract.admin_signed = True
        else:
            contract.user_signed = True

        contract.save()

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
        excel_file = request.FILES['file']

        # Fetch the selected template
        try:
            template = ContractTemplate.objects.get(id=template_id)
        except ContractTemplate.DoesNotExist:
            messages.error(request, "Selected template does not exist.")
            return redirect('generate_contracts')

        # Read Excel data
        data = pd.read_excel(excel_file).to_dict(orient='records')

        # Generate contracts
        contracts = []
        for row in data:
            filled_content = template.template_content
            for key, value in row.items():
                filled_content = filled_content.replace(f'{{{{ {key} }}}}', str(value))

            contracts.append(Contract(content=filled_content))

        # Bulk save contracts
        Contract.objects.bulk_create(contracts)
        messages.success(request, f"{len(contracts)} contracts generated successfully!")
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