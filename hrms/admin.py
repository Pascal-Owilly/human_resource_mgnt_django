from django.contrib import admin
from .models import Employee,Department,Attendance,Kin, User, Admin, Client, AccountManager
# Register your models here.
admin.site.register([User, Employee,Department,Attendance,Kin, Admin, Client, AccountManager])
