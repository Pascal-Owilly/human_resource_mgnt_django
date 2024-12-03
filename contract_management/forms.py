from django import forms
from jsignature.forms import JSignatureField

class ContractSignatureForm(forms.Form):
    signature = JSignatureField()
