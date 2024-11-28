from django.db import models

class Placeholder(models.Model):
    name = models.CharField(max_length=255)  # Placeholder name (e.g., 'Full Name')
    key = models.CharField(max_length=50, unique=True)  # Unique key (e.g., 'full_name')

    def __str__(self):
        return self.name

class ContractTemplate(models.Model):
    name = models.CharField(max_length=255)
    template_content = models.TextField()  # Contract content with placeholders
    placeholders = models.ManyToManyField(Placeholder)  # Selectable placeholders
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.name

class Contract(models.Model):
    template = models.ForeignKey(ContractTemplate, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contract for {self.template.name} ({self.created_at})"
