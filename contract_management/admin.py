from django.contrib import admin
from .models import Placeholder, ContractTemplate, Contract, Memo

admin.site.register([Placeholder, ContractTemplate, Contract, Memo])

