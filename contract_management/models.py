from django.db import models
from hrms.models import User

class Placeholder(models.Model):
    name = models.CharField(max_length=255)  # Placeholder name (e.g., 'Full Name')
    key = models.CharField(max_length=50, unique=True)  # Unique key (e.g., 'full_name')

    def __str__(self):
        return self.name

class ContractTemplate(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    template_content = models.TextField()  # Contract content with placeholders
    placeholders = models.ManyToManyField(Placeholder)  # Selectable placeholders
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"Contract for {self.id}"

class Contract(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    template = models.ForeignKey(ContractTemplate, on_delete=models.CASCADE)
    content = models.TextField()
    user_signed = models.BooleanField(default=False)
    admin_signed = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    signature = models.TextField(blank=True, null=True)  # For storing signature data
    initials = models.CharField(max_length=5, blank=True, null=True)  # For initials
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def is_fully_signed(self):
        return self.user_signed and self.admin_signed

    def __str__(self):
        return f"Contract for {self.template.name} ({self.created_at})"

# Contract signature
from jsignature.fields import JSignatureField

class ContractSignature(models.Model):
    full_name = models.CharField(max_length=255)    
    signature = JSignatureField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"Signature for {self.full_name} - ({self.created_at})"
