from django.shortcuts import render, redirect, get_object_or_404
from .models import ContractTemplate, Placeholder, Contract  # Ensure correct models are imported
from hrms.models import User
from django.template import Template, Context
from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from twilio.rest import Client  # Twilio for SMS
from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Signer, SignHere, Tabs, Recipients
import base64

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


def user_search(request):
    query = request.GET.get('q', '')
    if query:
        # Use phone number search instead of email
        users = User.objects.filter(phone_number__icontains=query)[:10]  # Adjust the filter logic as needed
        user_list = [{"id": user.id, "name": user.get_full_name(), "phone_number": user.phone_number} for user in users]
        return JsonResponse(user_list, safe=False)
    return JsonResponse([], safe=False)


from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.mail import send_mail
from .models import Contract
from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Signer, SignHere, Tabs, Recipients
import base64

def contract_preview(request, contract_id):
    contract = get_object_or_404(Contract, pk=contract_id)

    if request.method == "POST":
        if "agree_to_contract" not in request.POST:
            return JsonResponse({"success": False, "message": "You must agree to the contract terms before signing."})

        recipient_email = request.POST.get("recipient_email")
        recipient_name = request.POST.get("recipient_name", "User")  # Replace with the recipient's name if available

        if recipient_email:
            try:
                # DocuSign API Client Setup
                api_client = ApiClient()
                api_client.set_default_header("Authorization", "Bearer YOUR_ACCESS_TOKEN")  # Replace with a valid OAuth token
                api_client.host = "https://demo.docusign.net/restapi"  # DocuSign demo environment URL

                # Read contract content as Base64
                with open(contract.file.path, "rb") as file:
                    document_base64 = base64.b64encode(file.read()).decode("utf-8")

                # Create the signer and signature tab
                signer = Signer(
                    email=recipient_email,
                    name=recipient_name,
                    recipient_id="1",
                    routing_order="1",
                    client_user_id="12345"  # Needed for embedded signing
                )

                sign_here = SignHere(
                    anchor_string="Sign Here",
                    anchor_units="pixels",
                    anchor_y_offset="10",
                    anchor_x_offset="10"
                )

                signer.tabs = Tabs(sign_here_tabs=[sign_here])

                # Create the envelope
                envelope_definition = EnvelopeDefinition(
                    email_subject="Please Sign This Contract",
                    documents=[
                        {
                            "document_base64": document_base64,
                            "name": "Contract",
                            "file_extension": "pdf",
                            "document_id": "1",
                        }
                    ],
                    recipients=Recipients(signers=[signer]),
                    status="sent",
                )

                # Send the envelope
                envelopes_api = EnvelopesApi(api_client)
                envelope_summary = envelopes_api.create_envelope(account_id="YOUR_ACCOUNT_ID", envelope_definition=envelope_definition)

                # Create recipient view for embedded signing
                recipient_view_request = {
                    "authentication_method": "email",
                    "client_user_id": "12345",  # Same as the `client_user_id` set for the signer
                    "recipient_id": "1",
                    "return_url": "https://yourdomain.com/contract/completed",  # URL to redirect after signing
                    "user_name": recipient_name,
                    "email": recipient_email,
                }

                # Generate the signing URL
                recipient_view = envelopes_api.create_recipient_view(
                    account_id="YOUR_ACCOUNT_ID",
                    envelope_id=envelope_summary.envelope_id,
                    recipient_view_request=recipient_view_request,
                )

                # Send email notification
                send_mail(
                    subject="Contract Sent for Signature",
                    message=f"Hello {recipient_name},\n\nYour contract has been sent for signing via DocuSign. Envelope ID: {envelope_summary.envelope_id}\n\nThank you.",
                    from_email="your-email@example.com",
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )

                # Redirect to DocuSign signing URL
                return redirect(recipient_view.url)

            except Exception as e:
                return JsonResponse({"success": False, "message": str(e)})

    return render(request, 'contract_management/contract_preview.html', {'contract': contract})
    

# View to list all contract templates
def template_list(request):
    templates = ContractTemplate.objects.all()  # Fetch all templates
    return render(request, 'contract_management/template_list.html', {'templates': templates})

# View to list all generated contracts
def contract_list(request):
    contracts = Placeholder.objects.all()  # Fetch all contracts
    return render(request, 'contract_management/contract_list.html', {'contracts': contracts})

# Bulk csv
import csv

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

