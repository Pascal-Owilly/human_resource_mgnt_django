from django.contrib import admin
from .models import Placeholder, ContractTemplate

admin.site.register([Placeholder, ContractTemplate])

# @admin.register(Placeholder)
# class PlaceholderAdmin(admin.ModelAdmin):
#     list_display = ("name",)

# @admin.register(ContractTemplate)
# class ContractTemplateAdmin(admin.ModelAdmin):
#     list_display = ("recipient_email", "created_at", "template")
