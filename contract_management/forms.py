from django import forms
from jsignature.forms import JSignatureField
from .models import ContractTemplate, Memo
from hrms.models import User, AccountManager, Employee, HumanResourceManager

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

# Memo Form with dynamic choices handling
class MemoForm(forms.ModelForm):
    class Meta:
        model = Memo
        fields = ['title', 'body', 'recipients_category']

    def __init__(self, *args, **kwargs):
        super(MemoForm, self).__init__(*args, **kwargs)
        
        # Dynamically populate categories
        categories = [('all', 'All Users')]  # Default option
        if Employee.objects.exists():
            categories.append(('employee', 'Employees'))
        if AccountManager.objects.exists():
            categories.append(('account_manager', 'Account Managers'))
        if HumanResourceManager.objects.exists():
            categories.append(('human_resource_manager', 'HR Managers'))
        
        self.fields['recipients_category'].choices = categories
