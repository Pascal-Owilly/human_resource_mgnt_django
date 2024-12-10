from django import forms
from jsignature.forms import JSignatureField
from .models import ContractTemplate

class ContractSignatureForm(forms.Form):
    signature = JSignatureField()
    
class ExcelUploadForm(forms.Form):
    file = forms.FileField(label='Upload Excel File')

class ContractTemplateForm(forms.ModelForm):
    class Meta:
        model = ContractTemplate
        fields = ['name', 'template_content', 'placeholders']
        widgets = {
            'template_content': forms.Textarea(attrs={'rows': 10, 'cols': 80}),
            'placeholders': forms.CheckboxSelectMultiple,
        }