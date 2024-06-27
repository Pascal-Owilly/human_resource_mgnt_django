from django.db import models
import random
from django.urls import reverse
from django.utils import timezone
import time
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
import uuid
import string

class Department(models.Model):
    name = models.CharField(max_length=70, null=False, blank=False)
    branch = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("hrms:dept_detail", kwargs={"pk": self.pk})

class Client(models.Model):
    name = models.CharField(max_length=70, null=False, blank=False)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.CharField(max_length=100, null=True, blank=True)
    account_manager = models.ForeignKey('hrms.AccountManager', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("hrms:clnt_detail", kwargs={"pk": self.pk})


def generate_short_id(prefix, model_class, field_name, length=4):
    while True:
        new_id = prefix + ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        if not model_class.objects.filter(**{field_name: new_id}).exists():
            return new_id

def generate_emp_id():
    return generate_short_id('emp-', User, 'emp_id')

def generate_mng_id():
    return generate_short_id('mng-', User, 'mng_id')

class User(AbstractUser):

    SUPERUSER = 'superuser'
    EMPLOYEE= 'employee'
    ACCOUNT_MANAGER = 'account_manager'
    HUMAN_RESOURCE_MANAGER = 'human_resource_manager'
    CLIENT = 'client'
    CAN_CLOCK_IN_ANYWHERE = 'can_clockin_anywhere'
    NO_PRIVILEGES = 'Within the organization'
    NO_ROLE = 'no_role'

    ROLE_CHOICES = [
        (SUPERUSER, 'Superuser'),
        (EMPLOYEE, 'Employee'),
        (ACCOUNT_MANAGER, 'AccountManager'),
        (HUMAN_RESOURCE_MANAGER, 'Human resource manager'),
        (CLIENT, 'Client'),
        (CAN_CLOCK_IN_ANYWHERE, 'Can clock in from anywhere'),
        (NO_PRIVILEGES, 'Cannot clock in from anywhere'),
        (NO_ROLE, 'No role'),

    ]

    PRIVILEGE_CHOICES = [
        (NO_PRIVILEGES, 'No privileges'),
        (CAN_CLOCK_IN_ANYWHERE, 'Can clock in from anywhere'),
    ]

    LANGUAGE = (('english','ENGLISH'), ('french','FRENCH'), ('yoruba','YORUBA'),('hausa','HAUSA'))
    GENDER = (('male','MALE'), ('female', 'FEMALE'))

    role = models.CharField(max_length=255, choices=ROLE_CHOICES, default=NO_ROLE)
    clockin_privileges = models.CharField(max_length=255, choices=PRIVILEGE_CHOICES, default=NO_PRIVILEGES)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    username = models.CharField(max_length=30, unique=True)
    thumb = models.ImageField(blank=True, null=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=11, null=True, blank=True)
    address = models.CharField(max_length=100, null=True, blank=True)

    emp_id = models.CharField(max_length=70, unique=True, editable=False)
    mng_id = models.CharField(max_length=70, unique=True, editable=False)
    emergency_contact = models.CharField(max_length=11, null=True, blank=True)
    gender = models.CharField(choices=GENDER, max_length=10, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)

    is_archived = models.BooleanField(default=False)

    language = models.CharField(choices=LANGUAGE, max_length=10, default='english')
    nuban = models.CharField(max_length=10, default='0123456789')
    bank = models.CharField(max_length=25, default='Equity')
    salary = models.CharField(max_length=16, default='00,000.00')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    def save(self, *args, **kwargs):
        if not self.emp_id:
            self.emp_id = self.generate_emp_id()
        if not self.mng_id:
            self.mng_id = self.generate_mng_id()
        super().save(*args, **kwargs)

    def generate_emp_id(self):
        return self.generate_short_id('emp-', 'emp_id')

    def generate_mng_id(self):
        return self.generate_short_id('mng-', 'mng_id')
        
    # check if the user is available to avoid errors 
    def generate_short_id(self, prefix, field_name, length=4):
        while True:
            new_id = prefix + ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
            if not User.objects.filter(**{field_name: new_id}).exists():
                return new_id

    def get_absolute_url(self):
        return reverse("hrms:dept_detail", kwargs={"pk": self.pk})

class AccountManager(models.Model):
    account_manager = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f'{self.account_manager.first_name} {self.account_manager.last_name}'
        
    def get_absolute_url(self):
        return reverse("hrms:account_manager_view", kwargs={"pk": self.pk})
    
class Employee(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f'{self.employee.first_name} {self.employee.last_name}'
        
    def get_absolute_url(self):
        return reverse("hrms:employee_view", kwargs={"pk": self.pk})

class HumanResourceManager(models.Model):
    human_resource_manager = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f'{self.human_resource_manager.first_name} {self.human_resource_manager.last_name}'
        
    def get_absolute_url(self):
        return reverse("hrms:human_resource_manager_view", kwargs={"pk": self.pk})
  
class Admin(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f'{self.admin.first_name} {self.admin.last_name}'
        
    def get_absolute_url(self):
        return reverse("hrms:admin_view", kwargs={"pk": self.pk})
    

class Kin(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    address = models.TextField(max_length=100)
    occupation = models.CharField(max_length=20)
    mobile = models.CharField(max_length=15)
    employee = models.OneToOneField(Employee,on_delete=models.CASCADE, blank=False, null=False)

    def __str__(self):
        return self.first_name+'-'+self.last_name
    
    def get_absolute_url(self):
        return reverse("hrms:employee_view",kwargs={'pk':self.employee.pk})
    

class Attendance (models.Model):
    STATUS = (('SHORT BREAK', 'SHORT BREAK'), ('LUNCH BREAK', 'LUNCH BREAK'), ('ON LEAVE', 'ON LEAVE'))
    date = models.DateField(auto_now_add=True, null=True, blank=True)
    first_in = models.TimeField()
    last_out = models.TimeField(null=True)
    status = models.CharField(choices=STATUS, max_length=15 )
    staff = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True)
    account_manager = models.ForeignKey(AccountManager, on_delete=models.SET_NULL, null=True)

    latitude = models.FloatField(null=True, blank=True) 
    longitude = models.FloatField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.pk:  # If it's a new object (i.e., first in)
            self.first_in = timezone.localtime()
        else:  # If it's an existing object being updated (i.e., last out)
            self.last_out = timezone.localtime()
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Attendance -> '+str(self.date) + ' -> ' + str(self.staff)

class Leave (models.Model):
    STATUS = (('approved','APPROVED'),('unapproved','UNAPPROVED'),('decline','DECLINED'))
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    start = models.CharField(blank=False, max_length=15)
    end = models.CharField(blank=False, max_length=15)
    status = models.CharField(choices=STATUS,  default='Not Approved',max_length=15)

    def __str__(self):
        return self.employee + ' ' + self.start

class Recruitment(models.Model):
    first_name = models.CharField(max_length=25)
    last_name= models.CharField(max_length=25)
    position = models.CharField(max_length=15)
    email = models.EmailField(max_length=25)
    phone = models.CharField(max_length=11)

    def __str__(self):
        return self.first_name +' - '+self.position
