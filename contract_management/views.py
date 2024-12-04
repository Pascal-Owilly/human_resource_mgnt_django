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
def contract_list(request):
    # Fetch all contracts
    contracts = Contract.objects.all().select_related('template', 'user').order_by('-created_at')
    
    # Pass contracts to the template for rendering
    return render(request, 'contract_management/contract_list.html', {'contracts': contracts})

@login_required
def contract_preview(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    contract_templates = ContractTemplate.objects.all()

    email_sent = contract.email_sent  # Get the email_sent status from the model
    recipient_email = None
    recipient_name = None  # Initialize recipient_name to None

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

                # Return JsonResponse with recipient email and name
                return JsonResponse({
                    "success": True,
                    "message": "Email sent successfully.",
                    "recipient_email": recipient_email,
                    'recipient_name': recipient_name,
                })
            
            except User.DoesNotExist:
                return JsonResponse({"success": False, "message": "User with the provided email does not exist."})

        return JsonResponse({"success": False, "message": "Recipient email is required."})

    # Ensure recipient_name is passed even if the form hasn't been submitted
    return render(request, 'contract_management/contract_preview.html', {
        'contract': contract,
        'contract_templates': contract_templates,
        'email_sent': email_sent,
        'recipient_email': recipient_email,  # Ensure this is passed in the context
        'recipient_name': recipient_name,  # Safely pass recipient_name to template
    })


@login_required
def sign_contract_user(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)
    if request.method == "POST":
        contract.user_signed = True
        contract.save()
        return JsonResponse({"status": "success", "message": "Contract signed by user."})
    return JsonResponse({"status": "error", "message": "Invalid request."})

@login_required
def sign_contract_admin(request, contract_id):
    if not request.user.is_staff:
        return JsonResponse({"status": "error", "message": "Unauthorized."})

    contract = get_object_or_404(Contract, id=contract_id)
    if request.method == "POST":
        contract.admin_signed = True
        contract.save()
        return JsonResponse({"status": "success", "message": "Contract signed by admin."})
    return JsonResponse({"status": "error", "message": "Invalid request."})
    
@login_required
def combined_contract_and_template_list(request):
    # Fetch contracts and templates
    contracts = Contract.objects.all().select_related('template', 'user').order_by('-created_at')
    templates = ContractTemplate.objects.all()

    # Pagination for contracts (15 per page)
    contract_paginator = Paginator(contracts, 15)  # 15 contracts per page
    contract_page_number = request.GET.get('contract_page')  # Get current page number
    contract_page = contract_paginator.get_page(contract_page_number)

    # Pagination for templates (5 per page)
    template_paginator = Paginator(templates, 5)  # 5 templates per page
    template_page_number = request.GET.get('template_page')  # Get current page number
    template_page = template_paginator.get_page(template_page_number)

    # Pass both paginated contracts and templates to the template
    return render(request, 'contract_management/template_list.html', {
        'contracts': contract_page,
        'templates': template_page
    })


# List all Generated Contracts
@login_required
def contract_list(request):
    contracts = Contract.objects.all()
    return render(request, 'contract_management/contract_list.html', {'contracts': contracts})

# Bulk upload contracts from CSV
@login_required
def bulk_upload_contracts(request, template_id):
    template = get_object_or_404(ContractTemplate, pk=template_id)

    if request.method == 'POST':
        csv_file = request.FILES['file']
        reader = csv.DictReader(csv_file.read().decode('utf-8').splitlines())
        for row in reader:
            placeholder_values = {key: row[key] for key in template.placeholders.values_list('key', flat=True)}
            template_content = Template(template.template_content)
            context = Context(placeholder_values)
            filled_contract = template_content.render(context)
            Contract.objects.create(template=template, content=filled_contract)

        return redirect('hrms:contract_list')

    return render(request, 'contract_management/bulk_upload.html')

# Sign contract (using jsignature)
@login_required
def sign_contract(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    
    if request.method == 'POST':
        form = ContractSignatureForm(request.POST)
        if form.is_valid():
            signature = form.cleaned_data['signature']
            contract.signature = signature
            contract.save()
            return redirect('hrms:contract_success', contract_id=contract.id)
    else:
        form = ContractSignatureForm()

    return render(request, 'contract_management/sign_contract.html', {'form': form, 'contract': contract})






































