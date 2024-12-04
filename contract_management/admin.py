from django.contrib import admin
from .models import Placeholder, ContractTemplate, Contract

admin.site.register([Placeholder, ContractTemplate, Contract])

