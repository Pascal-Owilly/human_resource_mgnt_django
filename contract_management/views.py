from django.shortcuts import render, redirect, get_object_or_404
from .models import ContractTemplate, Placeholder, Contract
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


# User Search for Contract Signatories
def user_search(request):
    query = request.GET.get('q', '').strip()
    if query:
        # Search users by first_name, last_name, username, phone_number, or email using OR conditions
        users = User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(email__icontains=query)
        )[:10]

        # Build a list of user data with first_name, last_name, username, phone_number, and email
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
def create_contract(request, template_id):
    template = get_object_or_404(ContractTemplate, pk=template_id)

    if request.method == 'POST':
        # Collect values for the selected placeholders
        placeholder_values = {}
        for placeholder in template.placeholders.all():
            value = request.POST.get(placeholder.key, f"[{placeholder.name}]")  # Default to placeholder name if not provided
            placeholder_values[placeholder.key] = value

        # Render the contract with the placeholders
        template_content = Template(template.template_content)
        context = Context(placeholder_values)
        filled_contract = template_content.render(context)

        # Save the contract
        contract = Contract.objects.create(template=template, content=filled_contract)

        # Redirect to a contract preview page
        return redirect('hrms:contract_preview', contract_id=contract.id)

    return render(request, 'contract_management/create_contract.html', {'template': template})

# Contract preview and signature
def contract_preview(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)

    if request.method == 'POST':
        recipient_email = request.POST.get('recipient_email')
        if recipient_email:
            # Generate the URL for the contract review page using reverse
            contract_review_url = request.build_absolute_uri(reverse('hrms:contract_preview', args=[contract.id]))

            # Prepare the email content using the HTML template
            subject = "Contract Notification"
            html_message = render_to_string('emails/contract_notification.html', {
                'recipient_name': f"{contract.user.first_name} {contract.user.last_name}",
                'contract_id': contract.id,
                'contract_link': contract_review_url,  # Dynamic contract review link
            })
            
            # Create a plain text fallback for email clients that don't support HTML
            plain_message = f"""
                Hello {contract.user.first_name} {contract.user.last_name},

                You have a pending contract to review and sign.

                Contract ID: {contract.id}  
                Role: {contract.role}
                Start Date: {contract.start_date}
                End Date: {contract.end_date}
                Status: {contract.status}

                Please visit the following link to review and sign the contract:
                {contract_review_url}

                Best regards,
                Your Company Name
            """

            email_from = settings.DEFAULT_FROM_EMAIL
            recipient_list = [recipient_email]

            # Send the email with both plain text and HTML
            send_mail(
                subject,
                plain_message,
                email_from,
                recipient_list,
                html_message=html_message,  # HTML version
            )
            return JsonResponse({"success": True, "message": "Email sent successfully."})

        return JsonResponse({"success": False, "message": "Recipient email is required."})

    return render(request, 'contract_management/contract_preview.html', {'contract': contract})

# List all contract templates
def template_list(request):
    templates = ContractTemplate.objects.all()
    return render(request, 'contract_management/template_list.html', {'templates': templates})

# List all Generated Contracts  
def contract_list(request):
    contracts = Contract.objects.all()  # Fetch all contracts
    return render(request, 'contract_management/contract_list.html', {'contracts': contracts})

# Bulk upload contracts from CSV
def bulk_upload_contracts(request, template_id):
    template = get_object_or_404(ContractTemplate, pk=template_id)

    if request.method == 'POST':
        csv_file = request.FILES['file']

        # Process the CSV
        reader = csv.DictReader(csv_file.read().decode('utf-8').splitlines())
        for row in reader:
            placeholder_values = {key: row[key] for key in template.placeholders.values_list('key', flat=True)}

            # Render the contract
            template_content = Template(template.template_content)
            context = Context(placeholder_values)
            filled_contract = template_content.render(context)

            # Save the contract
            Contract.objects.create(template=template, content=filled_contract)

        return redirect('contract_list')

    return render(request, 'contract_management/bulk_upload.html')

# Sign contract (using jsignature)
def sign_contract(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)
    
    if request.method == 'POST':
        form = ContractSignatureForm(request.POST)
        if form.is_valid():
            # Capture the signature from the form data
            
            signature = form.cleaned_data['signature']
            contract.signature = signature  # Save the signature (base64 or image)
            contract.save()
            return redirect('contract_success', contract_id=contract.id)  # Redirect to success page
    
    else:
        form = ContractSignatureForm()

    return render(request, 'contract_management/sign_contract.html', {'form': form, 'contract': contract})
