from django.contrib.auth import get_user_model
from .models import Employee,Department,Kin,Attendance, Leave, Recruitment, Client, User
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django import forms
from django.core import validators
from django.utils import timezone
from django.db.models import Q
import time
from django import forms

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'role', 'clockin_privileges', 'first_name', 'last_name', 'username', 'thumb',
            'email', 'phone_number', 'address', 'emergency_contact', 'gender', 'department', 'is_archived'
        ]
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'clockin_privileges': forms.Select(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'thumb': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'is_archived': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

        }

class SuperuserRegistrationForm (UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Username'}))
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'First Name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Last Name'}))
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'+254712345678'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control','placeholder':'Valid Email is required'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control', 'placeholder':'Password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control', 'placeholder':'Confirm Password'}))
    thumb = forms.ImageField(label='Attach a Passport Photograph',required=True,widget=forms.FileInput(attrs={'class':'form-control mt-2'}))

    class Meta:
        model = get_user_model()
        fields = ('username','email','password1', 'password2','thumb', 'first_name', 'last_name', 'mobile')

class EmployeeRegistrationForm(UserCreationForm):

    username = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control','placeholder':'Valid Email is required'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control', 'placeholder':'Password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control', 'placeholder':'Confirm Password'}))
    thumb = forms.ImageField(label='Attach a Passport Photograph',required=True,widget=forms.FileInput(attrs={'class':'form-control mt-2'}))
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'First Name'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Last Name'}))
    mobile = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Mobile Number'}))
    address = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Address'}))
    emergency = forms.CharField(max_length=11, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Emergency Contact'}))
    gender = forms.ChoiceField(choices=(('male', 'Male'), ('female', 'Female')), widget=forms.Select(attrs={'class':'form-control'}))
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=False, empty_label='Select a department', widget=forms.Select(attrs={'class':'form-control'}))
    client = forms.ModelChoiceField(queryset=Client.objects.all(), required=False, empty_label='Select a Client', widget=forms.Select(attrs={'class':'form-control'}))
    privileges = forms.ChoiceField(choices=get_user_model().PRIVILEGE_CHOICES, widget=forms.Select(attrs={'class':'form-control'}))  # Assuming you have PRIVILEGE_CHOICES in your User model

    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'thumb', 'first_name', 'last_name', 'mobile', 'address', 'emergency', 'gender', 'department', 'privileges' , 'password1', 'password2',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Username"
        self.fields['email'].label = "Email"
        # You can add more custom labels or other customization if needed


class AccountManagerRegistrationForm(UserCreationForm):
    
    username = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control','placeholder':'Valid Email is required'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control', 'placeholder':'Password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control', 'placeholder':'Confirm Password'}))
    thumb = forms.ImageField(label='Attach a Passport Photograph',required=True,widget=forms.FileInput(attrs={'class':'form-control mt-2'}))
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'First Name'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Last Name'}))
    mobile = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Mobile Number'}))
    address = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Address'}))
    emergency = forms.CharField(max_length=11, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Emergency Contact'}))
    gender = forms.ChoiceField(choices=(('male', 'Male'), ('female', 'Female')), widget=forms.Select(attrs={'class':'form-control'}))
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=False, empty_label='Select a department', widget=forms.Select(attrs={'class':'form-control'}))
    client = forms.ModelChoiceField(queryset=Client.objects.all(), required=False, empty_label='Select a Client', widget=forms.Select(attrs={'class':'form-control'}))
    privileges = forms.ChoiceField(choices=get_user_model().PRIVILEGE_CHOICES, widget=forms.Select(attrs={'class':'form-control'}))  # Assuming you have PRIVILEGE_CHOICES in your User model

    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'thumb', 'first_name', 'last_name', 'mobile', 'address', 'emergency', 'gender', 'department', 'privileges' , 'password1', 'password2',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Username"
        self.fields['email'].label = "Email"
        # You can add more custom labels or other customization if needed

# EmployeeRegistration

class UploadFileForm(forms.Form):
    file = forms.FileField()

class LoginForm(AuthenticationForm):
   username = forms.CharField(widget=forms.TextInput(attrs={'autofocus':True, 'placeholder':'Username Here', 'class':'form-control'}))
   password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control', 'placeholder':'********'}))

# class EmployeeForm (forms.ModelForm):
#     thumb = forms.ImageField(widget=forms.ClearableFileInput(attrs={'class':'form-control'}))
#     first_name = forms.CharField(strip=True, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'First Name'}))
#     last_name = forms.CharField(strip=True, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Last Name'}))
#     mobile = forms.CharField(strip=True, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Mobile Number'}))
#     email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control','placeholder':'Valid Email'}))
#     emergency = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Relative Mobile Number'}))
#     gender = forms.ChoiceField(choices=Employee.GENDER,widget=forms.Select(attrs={'class':'form-control'}))
#     department = forms.ModelChoiceField(Department.objects.all(),required=True, empty_label='Select a department',widget=forms.Select(attrs={'class':'form-control'}))
#     language = forms.ChoiceField(choices=Employee.LANGUAGE,widget=forms.Select(attrs={'class':'form-control'}))

#     class Meta:
#         model = Employee
#         fields = ('first_name', 'last_name', 'mobile','email','emergency','salary','gender','department','bank','nuban','language','thumb')
#         widgets={
#             'salary':forms.TextInput(attrs={'class':'form-control'}),
#             'bank':forms.TextInput(attrs={'class':'form-control'}),
#             'nuban':forms.TextInput(attrs={'class':'form-control'})
#         }

class KinForm(forms.ModelForm):

    first_name = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class':'form-control'}))
    occupation = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control'}))
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control'}))
    employee = forms.ModelChoiceField(Employee.objects.filter(kin__employee=None),required=False,widget=forms.Select(attrs={'class':'form-control'}))

    class Meta:
        model = Kin
        fields = '__all__'
    
class DepartmentForm(forms.ModelForm):
    name = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Department Name'}))
    branch = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Enter Branch'}))
    description = forms.CharField(max_length=1000, widget=forms.Textarea(attrs={'class':'form-control', 'placeholder':'Brief Department Description'}))
    
    class Meta:
        model = Department
        fields = '__all__'

class ClientForm(forms.ModelForm):
    name = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Client Name'}))
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=False, empty_label='Select a department', widget=forms.Select(attrs={'class':'form-control'}))
    
    class Meta:
        model = Client
        fields = '__all__'

class AttendanceForm(forms.ModelForm):
    status = forms.ChoiceField(choices=Attendance.STATUS, widget=forms.Select(attrs={'class': 'form-control w-50'}))

    class Meta:
        model = Attendance
        fields = ['status']


class LeaveForm (forms.ModelForm):

    class Meta:
        model = Leave
        fields = '__all__'

        widgets={
            'start': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'end': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'status':forms.Select(attrs={'class':'form-control'}),
            'employee':forms.Select(attrs={'class':'form-control'}),
        }
class RecruitmentForm(forms.ModelForm):
    class Meta:
        model=Recruitment
        fields = '__all__'
        widgets = {
            'first_name':forms.TextInput(attrs={'class':'form-control'}),
            'last_name':forms.TextInput(attrs={'class':'form-control'}),
            'position':forms.TextInput(attrs={'class':'form-control'}),
            'email':forms.EmailInput(attrs={'class':'form-control'}),
            'phone':forms.TextInput(attrs={'class':'form-control'}),
        }
    
        