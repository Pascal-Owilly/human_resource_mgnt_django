from django.shortcuts import render,redirect, resolve_url,reverse, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from .models  import Employee, Department,Kin, Attendance, Leave, Recruitment, User, Admin, Client, HumanResourceManager
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, CreateView,View,DetailView,TemplateView,ListView,UpdateView,DeleteView
from .forms import SuperuserRegistrationForm,EmployeeRegistrationForm,LoginForm,KinForm,DepartmentForm,AttendanceForm, LeaveForm, RecruitmentForm, ClientForm
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordResetCompleteView
from django.views.generic import TemplateView
from datetime import datetime
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth import authenticate, login
from datetime import datetime, timedelta
from .serializers import AttendanceSerializer

# OTP

from .utils import generate_otp, store_otp, verify_otp

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

@method_decorator(csrf_exempt, name='dispatch')
class UserListView(View):
    template_name = 'hrms/users/user_list.html'
    paginate_by = 30  # Number of users per page

    def get(self, request):
        search_query = request.GET.get('search', '')

        # Constructing query based on search input
        users_list = User.objects.filter(
            is_archived=False
        ).filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(emergency_contact__icontains=search_query) |
            Q(client__name__icontains=search_query) |  # Assumes Client has a name field
            Q(address__icontains=search_query) |
            Q(role__icontains=search_query) |
            Q(emp_id__icontains=search_query) |
            Q(mng_id__icontains=search_query)
        ).order_by('-id')

        paginator = Paginator(users_list, self.paginate_by)
        page_number = request.GET.get('page')

        try:
            users = paginator.page(page_number)
        except PageNotAnInteger:
            users = paginator.page(1)
        except EmptyPage:
            users = paginator.page(paginator.num_pages)

        users_data = [
            {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'thumb_url': user.thumb.url if user.thumb else '/static/hrms/images/auth/default_profile.svg',
            }
            for user in users_list
        ]

        return render(request, self.template_name, {'users': users, 'search_query': search_query})
        
class UserDetailView(View, LoginRequiredMixin):
    template_name = 'hrms/users/user_detail.html'
    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        return render(request, self.template_name, {'user': user})

    def post(self, request, user_id):  # Ensure the method signature includes user_id
        user = get_object_or_404(User, pk=user_id)
        clockin_privileges = request.POST.get('clockin_privileges')
        if clockin_privileges:
            user.clockin_privileges = clockin_privileges
            user.save()
        return redirect('hrms:user_detail', user_id=user_id)

from .forms import UserUpdateForm

# User UpdateView

class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'hrms/users/user_update.html'
    success_url = reverse_lazy('hrms:user_list')
    login_url = 'hrms:login'

class UserArchiveView(LoginRequiredMixin, View):
    login_url = 'hrms:login'
    template_name = 'hrms/users/user_archive_confirm.html'  # Template for confirmation
    
    def get(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        return render(request, self.template_name, {'user': user})
    
    def post(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        user.is_archived = True
        user.save()
        return redirect(reverse_lazy('hrms:user_list'))

class UserUnarchiveView(LoginRequiredMixin, View):
    login_url = 'hrms:login'
    template_name = 'hrms/users/user_unarchive_confirm.html'  # Template for confirmation
    
    def get(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        return render(request, self.template_name, {'user': user})
    
    def post(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        user.is_archived = False
        user.save()
        return redirect(reverse_lazy('hrms:user_list'))

class ArchivedUserListView(ListView, LoginRequiredMixin):
    template_name = 'hrms/users/archived_user_list.html'
    paginate_by = 8  # Number of users per page
    context_object_name = 'users'
    
    def get_queryset(self):
        return User.objects.filter(is_archived=True).order_by('-id')

# User DeleteView
class UserDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    template_name = 'hrms/users/confirm_delete.html'
    success_url = reverse_lazy('hrms:user_list')
    login_url = 'hrms:login'

class Index(TemplateView):

   template_name = 'hrms/home/home.html'

def unauthorized(request):
    return render(request, 'auth/unauthorized.html')

def employee_dashboard(request):
    if request.user.role != 'employee' and not request.user.is_superuser:
        return redirect('unauthorized')
    return render(request, 'hrms/employees/employee_dashboard.html')


def send_password_reset_email(uidb64, token, email):
    reset_url = f"{settings.BASE_URL}{reverse('hrms:password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})}"
    subject = 'Set Your Password'
    message = f'Please click the following link to set your password: {reset_url}'
    sender_email = settings.DEFAULT_FROM_EMAIL

    send_mail(subject, message, sender_email, [email])

class CustomPasswordResetView(PasswordResetView):
    email_template_name = 'auth/send_password_reset_email.html'
    subject_template_name = 'auth/password_reset_subject.txt'
    template_name = 'auth/password_reset_form.html'
    success_url = reverse_lazy('hrms:password_reset_done')
    html_email_template_name = 'auth/send_password_reset_email.html'

    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        subject = render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())
        body = render_to_string(email_template_name, context)
        html_body = render_to_string(html_email_template_name, context)

        send_mail(subject, body, from_email, [to_email], html_message=html_body)

    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            user = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            form.add_error(None, 'User with this email doesnot exist. Check and try again')
            return self.form_invalid(form)        
        user = get_user_model().objects.get(email=email)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        context = {
            'email': email,
            'domain': settings.DOMAIN,
            'site_name': settings.SITE_NAME,
            'uidb64': uidb64,
            'user': user,
            'token': token,
            'protocol': 'https' if self.request.is_secure() else 'http',
            'password_reset_url': f"{settings.PROTOCOL}://{settings.DOMAIN}/reset/{uidb64}/{token}/",
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'theme_color': '#fdeb3d',
            'secondary_color': '#773697',
        }
        self.send_mail(
            self.subject_template_name,
            self.email_template_name,
            context,
            settings.DEFAULT_FROM_EMAIL,
            email,
            self.html_email_template_name,
        )
        
        return super().form_valid(form)
        
class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    success_url = reverse_lazy('hrms:password_reset_complete')
    template_name = 'auth/password_reset_confirm.html'

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'auth/password_reset_complete.html'
    success_url = reverse_lazy('hrms:password_reset_complete')

class CustomPasswordResetDoneView(TemplateView):
    template_name = 'auth/password_reset_done.html'

#   Authentication
class Register(CreateView):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)

    model = get_user_model()
    form_class = SuperuserRegistrationForm
    template_name = 'hrms/registrations/register.html'
    success_url = reverse_lazy('hrms:login')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.role = User.SUPERUSER
        user.is_superuser = True
        user.is_staff = True
        user.save()
        Admin.objects.create(admin=user)

        return redirect(self.success_url)

class CustomLoginView(LoginView):
    template_name = 'hrms/registrations/login.html'
    authentication_form = LoginForm

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(self.request, username=username, password=password)

        if user is not None:
            login(self.request, user)
            # Determine user's role and redirect accordingly
            if user.role == User.SUPERUSER:
                return redirect('/dashboard/admin/')  # Redirect admin users to admin page
            elif user.role == User.EMPLOYEE:
                return redirect('/dashboard/attendance/emp/')
            elif user.role == User.ACCOUNT_MANAGER:
                return redirect('/dashboard/account-manager/')  # Redirect employees to employee dashboard
            elif user.role == User.HUMAN_RESOURCE_MANAGER:
                return redirect('/dashboard/admin/')  # Redirect employees to employee dashboard
            else:
                # Handle other roles or scenarios
                return redirect('/')  # Redirect to a generic dashboard
        else:
            # Add a non-field error to the form indicating invalid username or password
            form.add_error(None, 'Invalid username or password.')
            return self.form_invalid(form)

    def form_invalid(self, form):
        # This method is called when the form is invalid
        return render(self.request, self.template_name, {'form': form})


class Logout_View(View):

    def get(self,request):
        logout(self.request)
        return redirect ('hrms:login',permanent=True)

class AdminDashboard(LoginRequiredMixin, ListView):
    login_url = 'hrms:login'
    model = get_user_model()
    template_name = 'hrms/dashboard/index.html'
    context_object_name = 'qset'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.role=='human_resource_manager':
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['emp_total'] = Employee.objects.all().count()
        context['hr_count'] = HumanResourceManager.objects.all().count()
        context['dept_total'] = Department.objects.all().count()
        context['client_total'] = Client.objects.all().count()
        context['users_count'] = get_user_model().objects.all().count()
        context['admin_count'] = Admin.objects.all().count()
        context['account_manager_count'] = AccountManager.objects.all().count()
        context['hr_manager_count'] = HumanResourceManager.objects.all().count()

        context['workers'] = Employee.objects.filter(employee__is_archived=False).order_by('-id')
        return context

class AdminListView(View):
    template_name = 'admin/admin_list.html'
    paginate_by = 8  # Number of users per page

    def get(self, request):
        admin_list = Admin.objects.all().order_by('-id')
        paginator = Paginator(admin_list, self.paginate_by)
        page_number = request.GET.get('page')

        try:
            admins = paginator.page(page_number)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page
            admins = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results
            admins = paginator.page(paginator.num_pages)

        return render(request, self.template_name, {'admins': admins})

class Admin_View(LoginRequiredMixin,DetailView):
    queryset = Admin.objects.select_related('admin__department').order_by('-id')
    template_name = 'hrms/admin/single.html'
    context_object_name = 'amin'
    login_url = 'hrms:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            query = Kin.objects.get(admin=self.object.pk)
            context["kin"] = query
            return context
        except ObjectDoesNotExist:
            return context

# Account Mnager views

from .forms import AccountManagerRegistrationForm
from .models import AccountManager

class AccountManagerDashboard(LoginRequiredMixin, ListView):
    login_url = 'hrms:login'
    model = AccountManager  # Adjust model to AccountManager if needed
    template_name = 'hrms/account_managers/index.html'
    context_object_name = 'clients'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'account_manager':
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        try:
            # Get the account manager instance
            account_manager = AccountManager.objects.get(account_manager=self.request.user)
            return account_manager.client_set.all()  # Assuming reverse relation is "client_set"
        except AccountManager.DoesNotExist:
            return Client.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Total number of employees (if needed)
        context['mng_emp_total'] = Employee.objects.all().count()
        
        # Total number of clients assigned to the account manager
        context['mng_client_total'] = self.get_queryset().count()
        
        # Other context data (example: workers list)
        context['workers'] = Employee.objects.filter(employee__is_archived=False).order_by('-id')
        
        return context


class AccountManager_New(LoginRequiredMixin, CreateView):
    model = AccountManager
    form_class = AccountManagerRegistrationForm
    template_name = 'hrms/account_managers/create.html'
    login_url = 'hrms:login'
    redirect_field_name = 'redirect:'
    success_url = reverse_lazy('hrms:account_manager_all')  

    @staticmethod
    def send_password_reset_email(uidb64, token, email, first_name, last_name, username):
        # Construct the reset password URL
        reset_url = f"{settings.PROTOCOL}://{settings.DOMAIN}/reset/{uidb64}/{token}/"

        # Construct the email message
        subject = 'Set Your Password'
        context = {
            'reset_url': reset_url,
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
            'theme_color': '#fdeb3d',
            'secondary_color': '#773697',
        }
        html_message = render_to_string('auth/password_reset_email.html', context)
        sender_email = settings.EMAIL_HOST_USER

        # Send the email
        send_mail(subject, None, sender_email, [email], html_message=html_message)

    def form_valid(self, form):

        # Generate a random password
        password = generate_random_password()

        # Save the form data
        user = form.save(commit=False)
        user.role = User.ACCOUNT_MANAGER
        user.set_password(password)  # Set the random password
        user.save()

        # Get the department from the form
        department = form.cleaned_data.get('department')

        # Generate uidb64 and token for password reset email
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Get user details
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        username = form.cleaned_data.get('username')

        # Send password reset email
        self.send_password_reset_email(uidb64, token, user.email, first_name, last_name, username)

        # Create a new Account manager and employee instance and associate the user with it
        AccountManager.objects.create(account_manager=user)
        Employee.objects.create(employee=user)

        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        return context

class Account_Manager_All(LoginRequiredMixin, ListView):
    template_name = 'hrms/account_managers/account_managers_list.html'
    model = AccountManager
    context_object_name = 'account_managers'
    paginate_by = 5
    login_url = 'hrms:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(account_manager__is_archived=False).order_by('-id')

class Account_Manager_View(LoginRequiredMixin,DetailView):
    queryset = Employee.objects.select_related('account_manager__department').order_by('-id')
    template_name = 'hrms/account_managers/single.html'
    context_object_name = 'account_manager'
    login_url = 'hrms:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            query = Client.objects.get(account_manager=self.object.pk)
            context["client"] = query
            return context
        except ObjectDoesNotExist:
            return context

# Employee views

class EmployeeDashboard(LoginRequiredMixin, ListView):
    login_url = 'hrms:login'
    model = get_user_model()
    template_name = 'hrms/employee/employee_dashboard.html'
    context_object_name = 'qset'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'employee' and not request.user.is_superuser:
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)

# Employee's

import string
import random
from.models import HumanResourceManager

def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

# Human resource manager

class HumanResourceManagerDashboard(LoginRequiredMixin, ListView):
    login_url = 'hrms:login'
    model = get_user_model()
    template_name = 'hrms/dashboard/index.html'
    context_object_name = 'qset'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.role=='human_resource_manager':
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['emp_total'] = Employee.objects.all().count()
        context['dept_total'] = Department.objects.all().count()
        context['client_total'] = Client.objects.all().count()
        context['users_count'] = get_user_model().objects.all().count()
        context['admin_count'] = Admin.objects.all().count()
        context['account_manager_count'] = AccountManager.objects.all().count()
        context['workers'] = Employee.objects.filter(employee__is_archived=False).order_by('-id')
        return context

from .forms import HumanResourceManagerRegistrationForm

class HumanResourceManagerNew(LoginRequiredMixin, CreateView):
    model = HumanResourceManager
    form_class = HumanResourceManagerRegistrationForm
    template_name = 'hrms/account_managers/hr_create.html'
    login_url = 'hrms:login'
    redirect_field_name = 'redirect:'
    success_url = reverse_lazy('hrms:hr_all')  # URL to redirect to after a successful registration

    @staticmethod
    def send_password_reset_email(uidb64, token, email, first_name, last_name, username):
        # Construct the reset password URL
        reset_url = f"{settings.PROTOCOL}://{settings.DOMAIN}/reset/{uidb64}/{token}/"

        # Construct the email message
        subject = 'Set Your Password'
        context = {
            'reset_url': reset_url,
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
            'theme_color': '#fdeb3d',
            'secondary_color': '#773697',
        }
        html_message = render_to_string('auth/password_reset_email.html', context)
        sender_email = settings.EMAIL_HOST_USER

        # Send the email
        send_mail(subject, None, sender_email, [email], html_message=html_message)

    def form_valid(self, form):

        # Generate a random password
        password = generate_random_password()

        # Save the form data
        user = form.save(commit=False)
        user.role = User.HUMAN_RESOURCE_MANAGER
        user.set_password(password)  # Set the random password
        user.save()

        # Get the department from the form
        department = form.cleaned_data.get('department')

        # Generate uidb64 and token for password reset email
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Get user details
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        username = form.cleaned_data.get('username')

        # Send password reset email
        self.send_password_reset_email(uidb64, token, user.email, first_name, last_name, username)

        # Create a new Employee instance and associate the user with it
        HumanResourceManager.objects.create(human_resource_manager=user)
        Employee.objects.create(employee=user)

        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        return context

# Bulk reistration
import pandas as pd
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

# Define a function to perform bulk registration
from django.shortcuts import render
from .forms import UploadFileForm
from .utils import process_uploaded_file

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            process_uploaded_file(file)
            return render(request, 'auth/employee_bulk_upload_success.html')
    else:
        form = UploadFileForm()
    return render(request, 'auth/employee_bulk_upload.html', {'form': form})


class Employee_All(LoginRequiredMixin, ListView):
    template_name = 'hrms/employee/index.html'
    model = Employee
    context_object_name = 'employees'
    paginate_by = 5
    login_url = 'hrms:login'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'human_resource_manager' and not request.user.is_superuser:
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(employee__is_archived=False).order_by('-id')

class Employee_View(LoginRequiredMixin,DetailView):
    queryset = Employee.objects.select_related('employee__client').order_by('-id')
    template_name = 'hrms/employee/single.html'
    context_object_name = 'employee'
    login_url = 'hrms:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            query = Kin.objects.get(employee=self.object.pk)
            context["kin"] = query
            return context
        except ObjectDoesNotExist:
            return context

class Employee_New(LoginRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeRegistrationForm
    template_name = 'hrms/employee/create.html'
    login_url = 'hrms:login'
    redirect_field_name = 'redirect:'
    success_url = reverse_lazy('hrms:employee_all')  # URL to redirect to after a successful registration

    @staticmethod
    def send_password_reset_email(uidb64, token, email, first_name, last_name, username):
        # Construct the reset password URL
        reset_url = f"{settings.PROTOCOL}://{settings.DOMAIN}/reset/{uidb64}/{token}/"

        # Construct the email message
        subject = 'Set Your Password'
        context = {
            'reset_url': reset_url,
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
            'theme_color': '#fdeb3d',
            'secondary_color': '#773697',
        }
        html_message = render_to_string('auth/password_reset_email.html', context)
        sender_email = settings.EMAIL_HOST_USER

        # Send the email
        send_mail(subject, None, sender_email, [email], html_message=html_message)

    def form_valid(self, form):

        # Generate a random password
        password = generate_random_password()

        # Save the form data
        user = form.save(commit=False)
        user.role = User.EMPLOYEE
        user.set_password(password)  # Set the random password
        user.save()

        # Get the department from the form
        department = form.cleaned_data.get('department')

        # Generate uidb64 and token for password reset email
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Get user details
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        username = form.cleaned_data.get('username')

        # Send password reset email
        self.send_password_reset_email(uidb64, token, user.email, first_name, last_name, username)

        # Create a new Employee instance and associate the user with it
        Employee.objects.create(employee=user)

        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        return context

class HumanResourceManagerAll(LoginRequiredMixin, ListView):
    template_name = 'hrms/account_managers/human_resource_managers_list.html'
    model = HumanResourceManager
    context_object_name = 'human_resource_managers'
    paginate_by = 5
    login_url = 'hrms:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.role=='human_resource_manager':
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(human_resource_manager__is_archived=False).order_by('-id')

class HumanResourceManagerView(LoginRequiredMixin,DetailView):
    queryset = Employee.objects.select_related('employee__client').order_by('-id')
    template_name = 'hrms/employee/single.html'
    context_object_name = 'employee'
    login_url = 'hrms:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            query = Kin.objects.get(employee=self.object.pk)
            context["kin"] = query
            return context
        except ObjectDoesNotExist:
            return context

class Employee_Update(LoginRequiredMixin, View):
    template_name = 'hrms/employee/edit.html'
    login_url = 'hrms:login'

    def get(self, request, pk, *args, **kwargs):
        employee = Employee.objects.get(pk=pk)
        form = EmployeeRegistrationForm(instance=employee)
        return render(request, self.template_name, {'form': form})

    def post(self, request, pk, *args, **kwargs):
        employee = Employee.objects.get(pk=pk)
        form = EmployeeRegistrationForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('success_url')  # Replace 'success_url' with your desired redirect URL
        return render(request, self.template_name, {'form': form})

class Employee_Delete(LoginRequiredMixin, DeleteView):
    model = Employee
    template_name = 'hrms/employee/confirm_delete.html'
    success_url = reverse_lazy('hrms:employee_all')  # Replace 'success_url' with your desired redirect URL
    login_url = 'hrms:login'

class Employee_Kin_Add (LoginRequiredMixin,CreateView):
    model = Kin
    form_class = KinForm
    template_name = 'hrms/employee/kin_add.html'
    login_url = 'hrms:login'


    def get_context_data(self):
        context = super().get_context_data()
        if 'id' in self.kwargs:
            emp = Employee.objects.get(pk=self.kwargs['id'])
            context['emp'] = emp
            return context
        else:
            return context

class Employee_Kin_Update(LoginRequiredMixin,UpdateView):
    model = Kin
    form_class = KinForm
    template_name = 'hrms/employee/kin_update.html'
    login_url = 'hrms:login'

    def get_initial(self):
        initial = super(Employee_Kin_Update,self).get_initial()

        if 'id' in self.kwargs:
            emp =  Employee.objects.get(pk=self.kwargs['id'])
            initial['employee'] = emp.pk

            return initial

# Department views
class DepartmentListView(View, LoginRequiredMixin):
    template_name = 'hrms/department/department_list.html'
    paginate_by = 5  # Number of users per page

    def get(self, request):
        department_list = Department.objects.all().order_by('-id')
        paginator = Paginator(department_list, self.paginate_by)
        page_number = request.GET.get('page')

        try:
            departments = paginator.page(page_number)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page
            departments = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results
            departments = paginator.page(paginator.num_pages)

        return render(request, self.template_name, {'departments': departments})

class Department_Detail(LoginRequiredMixin, ListView):
    context_object_name = 'employees'
    template_name = 'hrms/department/single.html'
    login_url = 'hrms:login'

    def get_queryset(self):
        department_pk = self.kwargs.get('pk')
        queryset = Employee.objects.filter(employee__department_id=department_pk)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        department_pk = self.kwargs.get('pk')
        department = get_object_or_404(Department, pk=department_pk)
        context["dept"] = department
        return context

class Department_New (LoginRequiredMixin,CreateView):
    model = Department
    template_name = 'hrms/department/create.html'
    form_class = DepartmentForm
    login_url = 'hrms:login'

class Department_Update(LoginRequiredMixin,UpdateView):
    model = Department
    template_name = 'hrms/department/edit.html'
    form_class = DepartmentForm
    login_url = 'hrms:login'
    success_url = reverse_lazy('hrms:dashboard')

# Client views 

class ClientListView(View, LoginRequiredMixin):
    template_name = 'hrms/client/client_list.html'
    paginate_by = 5  # Number of users per page

    def get(self, request):
        client_list = Client.objects.all().order_by('-id')
        paginator = Paginator(client_list, self.paginate_by)
        page_number = request.GET.get('page')

        try:
            clients = paginator.page(page_number)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page
            clients = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results
            clients = paginator.page(paginator.num_pages)

        return render(request, self.template_name, {'clients': clients})

from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from .models import Client

# class Client_Detail(LoginRequiredMixin, DetailView):
#     model = Client
#     context_object_name = 'clnt'
#     template_name = 'hrms/client/single.html'
#     login_url = 'hrms:login'

#     def get_object(self, queryset=None):
#         client_pk = self.kwargs.get('pk')
#         return get_object_or_404(Client, pk=client_pk)

class Client_Detail(LoginRequiredMixin, ListView):
    context_object_name = 'clients'
    template_name = 'hrms/client/single.html'
    login_url = 'hrms:login'

    def get_queryset(self):
        client_pk = self.kwargs.get('pk')
        queryset = Employee.objects.filter(employee__client_id=client_pk)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client_pk = self.kwargs.get('pk')
        client = get_object_or_404(Client, pk=client_pk)
        context["clnt"] = client
        return context


class Client_New(LoginRequiredMixin, CreateView):
    model = Client
    template_name = 'hrms/client/create.html'
    form_class = ClientForm
    login_url = 'hrms:login'

    def form_valid(self, form):
        # Add debugging output
        print("Form is valid. Cleaned data:", form.cleaned_data)
        return super().form_valid(form)

    def form_invalid(self, form):
        # Add debugging output
        print("Form is invalid. Errors:", form.errors)
        return super().form_invalid(form)

class Client_Update(LoginRequiredMixin,UpdateView):
    model = Client
    template_name = 'hrms/client/edit.html'
    form_class = ClientForm
    login_url = 'hrms:login'
    success_url = reverse_lazy('hrms:clnt_all')

    def get_object(self, queryset=None):
        # handle case where client does not exist
        return get_object_or_404(Client, pk=self.kwargs.get('pk'))

class AccountManagerClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'hrms/account_managers/account_manager_clients.html'
    context_object_name = 'clients'

    def get_queryset(self):
        try:
            # Get the AccountManager instance for the logged-in user
            account_manager = AccountManager.objects.get(account_manager=self.request.user)

            # Filter clients associated with the account manager
            return Client.objects.filter(account_manager=account_manager)
        except AccountManager.DoesNotExist:
            # Handle case where AccountManager instance does not exist for the logged-in user
            return Client.objects.none()  # Return an empty queryset

#Attendance View

from django.utils import timezone
from datetime import datetime

from django.core.paginator import Paginator

class Attendance_Admin(LoginRequiredMixin, View):
    login_url = 'hrms:login'

    def dispatch(self, request, *args, **kwargs):
            if request.user.role != 'human_resource_manager' and not request.user.is_superuser:
                return render(request, 'auth/unauthorized.html')
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Get query parameters
        date = request.GET.get('date')
        keyword = request.GET.get('keyword')
        geofence_center = (-1.315638, 36.862129)  # Example: Nairobi coordinates
        
        employee = request.user

        # Retrieve attendance records based on the provided date
        if date:
            try:
                selected_date = datetime.strptime(date, '%Y-%m-%d').date()
                present_staffers = Attendance.objects.filter(Q(status='PRESENT') & Q(date=selected_date)).order_by('-id')
            except ValueError:
                selected_date = None
                present_staffers = Attendance.objects.none()
        else:
            selected_date = timezone.localdate()
            present_staffers = Attendance.objects.filter(Q(status='PRESENT') & Q(date=selected_date)).order_by('-id')

        # Perform search if keyword is provided
        if keyword:
            present_staffers = present_staffers.filter(
                Q(user__first_name__icontains=keyword) |
                Q(user__last_name__icontains=keyword) |
                Q(user__username__icontains=keyword) |
                Q(user__email__icontains=keyword)
            )
         
        # Calculate distance for each present staffer
        for staff in present_staffers:
            if staff.latitude and staff.longitude:
                staff.distance = geodesic((staff.latitude, staff.longitude), geofence_center).meters
            else:
                staff.distance = None

        # Pagination
        paginator = Paginator(present_staffers, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
            
        # Check if the logged-in user is clocked in
        clocked_in = Attendance.objects.filter(
            user=employee, date=timezone.localdate(), last_out__isnull=True
        ).exists()

        context = {
            'today': timezone.localdate(),
            'present_staffers': page_obj,
            'selected_date': selected_date,
            'keyword': keyword,
            'page_obj': page_obj,
            'clocked_in': clocked_in
        }

        return render(request, 'hrms/attendance/create.html', context)

class Attendance_Account_Manager(LoginRequiredMixin, View):
    login_url = 'hrms:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.role == 'account_manager':
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        date = request.GET.get('date')
        keyword = request.GET.get('keyword')
        account_manager = AccountManager.objects.get(account_manager=request.user)
        clients = Client.objects.filter(account_manager=account_manager)
        
        # Retrieve the logged-in employee
        employee = request.user
        
        # Fetch employees associated with the account manager's clients
        client_employees = User.objects.filter(client__in=clients)

        # Fetch employees directly associated with the account manager

        # Combine both sets of employees
        employees = client_employees 
        print('client employees',employees)
        if date:
            try:
                selected_date = datetime.strptime(date, '%Y-%m-%d').date()
                present_staffers = Attendance.objects.filter(
                    Q(status='PRESENT') &
                    Q(date=selected_date) &
                    Q(user__in=employees)
                ).order_by('-id')
            except ValueError:
                selected_date = None
                present_staffers = Attendance.objects.none()
        else:
            selected_date = timezone.localdate()
            present_staffers = Attendance.objects.filter(
                Q(status='PRESENT') &
                Q(date=selected_date) &
                Q(user__in=employees)
            ).order_by('-id')

       # Check if the logged-in employee is clocked in
        clocked_in = Attendance.objects.filter(
            user=employee, date=timezone.localdate(), last_out__isnull=True
        ).exists()

        context = {
            'today': timezone.localdate(),
            'present_staffers': present_staffers,
            'selected_date': selected_date,
            'keyword': keyword,
            'clocked_in': clocked_in,  

        }

        return render(request, 'hrms/account_managers/attendance.html', context)


class Attendance_Employee(LoginRequiredMixin, View):
    login_url = 'hrms:login'

    def get(self, request, *args, **kwargs):
        # Get query parameters
        date_emp = request.GET.get('date')
        keyword = request.GET.get('keyword')
        geofence_center = (-1.315638, 36.862129)  # Example: Nairobi coordinates

        # Retrieve the logged-in employee
        employee = request.user

        # Determine the start and end of the current week (Monday to Friday)
        today_emp = timezone.localdate()
        start_of_week = today_emp - timedelta(days=today_emp.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=4)  # Friday

        # Retrieve attendance records for the logged-in employee within the current week
        if date_emp:
            try:
                selected_date = datetime.strptime(date_emp, '%Y-%m-%d').date()
                present_employees = Attendance.objects.filter(
                    Q(status='PRESENT') & Q(date=selected_date) & Q(user=employee)
                ).order_by('-id')
            except ValueError:
                selected_date = None
                present_employees = Attendance.objects.none()
        else:
            selected_date = None
            present_employees = Attendance.objects.filter(
                Q(status='PRESENT') & Q(date__range=(start_of_week, end_of_week)) & Q(user=employee)
            ).order_by('-id')

        # Perform search if keyword is provided
        if keyword:
            present_employees = present_employees.filter(
                Q(user__first_name__icontains=keyword) |
                Q(user__last_name__icontains=keyword)
            )

        # Calculate distance for each present staffer
        for staff in present_employees:
            if staff.latitude and staff.longitude:
                staff.distance = geodesic((staff.latitude, staff.longitude), geofence_center).meters
            else:
                staff.distance = None

        # Pagination
        paginator = Paginator(present_employees, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Check if the logged-in employee is clocked in
        clocked_in = Attendance.objects.filter(
            user=employee, date=timezone.localdate(), last_out__isnull=True
        ).exists()

        context = {
            'today_emp': today_emp,
            'present_employees': page_obj,
            'selected_date': selected_date,
            'keyword': keyword,
            'page_obj': page_obj,
            'clocked_in': clocked_in
        }

        return render(request, 'hrms/employee/employee_dashboard.html', context)


from geopy.distance import geodesic

class Attendance_Out(LoginRequiredMixin, View):
    login_url = 'hrms:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)


    def get(self, request, *args, **kwargs):
        try:
            user = Attendance.objects.get(
                Q(staff__id=self.kwargs['user_id']) &
                Q(status='PRESENT') &
                Q(date=timezone.localdate())
            )
            user.last_out = timezone.localtime()
            user.save()
            return redirect('hrms:attendance_new')
        except Attendance.DoesNotExist:
            return redirect('hrms:attendance_new')

class Attendance_Out_Account_Manager(LoginRequiredMixin, View):
    login_url = 'hrms:login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.role=='account_manager':
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)


    def get(self, request, *args, **kwargs):
        try:
            user = Attendance.objects.get(
                Q(user__id=self.kwargs['user_id']) &
                Q(status='PRESENT') &
                Q(date=timezone.localdate())
            )
            user.last_out = timezone.localtime()
            user.save()
            return redirect('hrms:account_manager_attendance_list')
        except Attendance.DoesNotExist:
            return redirect('hrms:account_manager_attendance_list')


class Attendance_Out_Emp(LoginRequiredMixin, View):
    login_url = 'hrms:login'

    def get(self, request, *args, **kwargs):
        try:
            user = Attendance.objects.get(
                Q(user__id=self.kwargs['user_id']) &
                Q(status='PRESENT') &
                Q(date=timezone.localdate())
            )
            user.last_out = timezone.localtime()
            user.save()
            return redirect('hrms:attendance_employee')
        except Attendance.DoesNotExist:
            return redirect('hrms:attendance_employee')

from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from geopy.distance import geodesic
from .models import Attendance, Employee  

class SendOTPView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'error': 'User not authenticated.'}, status=401)
        
        otp = generate_otp()
        store_otp(user, otp)
        
        # In production, send the OTP via SMS
        print(f'Generated OTP for {user.phone_number}: {otp}')  # For testing
        
        return JsonResponse({'message': 'OTP sent'}, status=200)

class VerifyOTPView(View):
    def post(self, request):
        user = request.user
        otp = request.POST.get('otp')
        if not otp:
            return JsonResponse({'error': 'OTP is required.'}, status=400)
        
        if verify_otp(user, otp):
            OTP.objects.filter(user=user).delete()  # Optional
            return JsonResponse({'message': 'OTP verified successfully'}, status=200)
        else:
            return JsonResponse({'error': 'Invalid OTP'}, status=400)

from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from geopy.distance import geodesic
from datetime import datetime
from .models import OTP

class ClockInView(View):
    def post(self, request, *args, **kwargs):
        phone_number = request.POST.get('phone_number')
        otp = request.POST.get('otp')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        user = request.user

        if not user.is_authenticated:
            messages.error(request, 'User not authenticated.')
            return self.redirect_based_on_role()

        if otp:
            # Verify OTP for clock-in only
            return self.verify_otp(user, otp, latitude, longitude)
        else:
            # Check if user is clocking out
            if Attendance.objects.filter(user=user, date=timezone.localdate(), last_out__isnull=True).exists():
                return self.handle_attendance(user, latitude, longitude, None)  # No OTP needed for clock-out
            else:
                # Generate and send OTP for clock-in
                return self.generate_and_send_otp(user, latitude, longitude)
    
    def generate_otp(self):
        import random
        return str(random.randint(100000, 999999))
    
    def send_otp(self, user, otp_code):
        # Send OTP via SMS or email
        subject = 'Your OTP Code'
        message = f'Your OTP code is {otp_code}.'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

    def verify_otp(self, user, otp, latitude, longitude):
        try:
            otp_record = OTP.objects.get(user=user, otp=otp)
            if otp_record.is_valid():
                if not (latitude and longitude):
                    messages.error(self.request, 'Location data required.')
                    return self.redirect_based_on_role()

                try:
                    user_location = (float(latitude), float(longitude))
                    distance_km = geodesic(user_location, (-1.3319954, 36.8622605)).km
                except ValueError:
                    messages.error(self.request, 'Invalid location data.')
                    return self.redirect_based_on_role()

                if user.clockin_privileges == User.CAN_CLOCK_IN_ANYWHERE or distance_km <= 0.3:
                    return self.handle_attendance(user, latitude, longitude, distance_km)
                else:
                    messages.error(self.request, 'Outside allowed geofence area.')
                    return self.redirect_based_on_role()
            else:
                return JsonResponse({'error': 'Invalid or expired OTP.'}, status=400)
        except OTP.DoesNotExist:
            return JsonResponse({'error': 'OTP not found.'}, status=400)
    
    def generate_and_send_otp(self, user, latitude, longitude):
        otp_code = self.generate_otp()
        expiry_time = timezone.now() + timezone.timedelta(minutes=10)
        OTP.objects.create(user=user, otp=otp_code, expiry_time=expiry_time)
        
        # Send OTP to user via SMS or email
        self.send_otp(user, otp_code)
        
        return JsonResponse({'otp_sent': True}, status=200)

    def handle_attendance(self, user, latitude, longitude, distance_km):
        attendance = Attendance.objects.filter(
            user=user,
            date=timezone.localdate(),
            last_out__isnull=True
        ).first()

        if attendance:
            attendance.last_out = timezone.localtime()
            attendance.save()
            message = 'Clock-out successful!'
        else:
            Attendance.objects.create(
                user=user,
                latitude=latitude,
                longitude=longitude,
                distance=distance_km,
                first_in=timezone.localtime(),
                status='PRESENT'
            )
            message = 'Clock-in successful!'
            self.send_late_arrival_notification(user)
        
        messages.success(self.request, message)
        return self.redirect_based_on_role()

    def send_late_arrival_notification(self, user):
        clock_in_time = timezone.localtime()
        if clock_in_time.time() > datetime.strptime('08:30', '%H:%M').time():
            subject = 'Late Clock-in Notification'
            html_message = render_to_string('hrms/employee/employee_late_arrival.html', {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'clock_in_time': clock_in_time.strftime("%H:%M:%S")
            })
            plain_message = strip_tags(html_message)
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = 'pascalouma55@gmail.com'

            send_mail(subject, plain_message, from_email, [to_email], html_message=html_message, fail_silently=False)

    def redirect_based_on_role(self):
        user = self.request.user
        role_redirects = {
            'employee': 'hrms:attendance_employee',
            'superuser': 'hrms:attendance_new',
            'human_resource_manager': 'hrms:attendance_new',
            'account_manager': 'hrms:account_manager_attendance_list'
        }
        return redirect(role_redirects.get(user.role, 'hrms:attendance_employee'))
            
from geopy.distance import geodesic
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from geopy.distance import geodesic
from .models import Attendance, Employee

import io
from django.http import HttpResponse
from django.template.loader import get_template
from django.views import View
from xhtml2pdf import pisa
import openpyxl
from .models import Attendance
from django.utils import timezone

class DownloadPDF(View, LoginRequiredMixin):
    def get(self, request, *args, **kwargs):
        date = request.GET.get('date', timezone.localdate())
        keyword = request.GET.get('keyword', '')

        # Filter Attendance records based on date and keyword
        attendances = Attendance.objects.filter(date=date)

        if keyword:
            attendances = attendances.filter(
                Q(user__first_name__icontains=keyword) |
                Q(user__last_name__icontains=keyword) |
                Q(user__username__icontains=keyword) |
                Q(user__email__icontains=keyword)
            )

        # Convert distance from km to meters and format to 2 decimal places
        for attendance in attendances:
            if attendance.distance is not None:
                attendance.distance_meters = f"{attendance.distance * 1000:.2f}"  # Convert km to meters and format
            else:
                attendance.distance_meters = 'N/A'

        # Pass the context to the template
        context = {
            'attendances': attendances,
            'date': date,
            'keyword': keyword,
        }

        # Render the PDF template
        template = get_template('hrms/attendance/download_data/pdf_template.html')
        html = template.render(context)

        # Create a PDF response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="attendance.pdf"'

        pisa_status = pisa.CreatePDF(
            io.BytesIO(html.encode('UTF-8')),
            dest=response,
        )

        if pisa_status.err:
            return HttpResponse('We had some errors with your request', status=500)
        return response

class DownloadExcel(View, LoginRequiredMixin):
    def get(self, request, *args, **kwargs):
        # Extract query parameters
        date = request.GET.get('date', timezone.localdate())
        keyword = request.GET.get('keyword', '')

        # Filter Attendance records based on date and keyword
        attendances = Attendance.objects.filter(date=date)

        if keyword:
            attendances = attendances.filter(
                Q(user__first_name__icontains=keyword) |
                Q(user__last_name__icontains=keyword) |
                Q(user__username__icontains=keyword) |
                Q(user__email__icontains=keyword)
            )

        # Create an HTTP response with Excel content
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="attendance_users.xlsx"'

        # Create a workbook and select the active worksheet
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = 'Attendance and Users'

        # Define the header row
        columns = ['Username', 'First Name', 'Last Name', 'Email', 'Date', 'First-In (Arrival)', 'Last-Out (Departure)', 'Distance (m)']
        row_num = 1

        # Write the header row
        for col_num, column_title in enumerate(columns, 1):
            cell = worksheet.cell(row=row_num, column=col_num)
            cell.value = column_title

        # Write attendance and user data rows
        for attendance in attendances:
            row_num += 1

            # Convert distance from km to meters and format to 2 decimal places
            distance_meters = attendance.distance * 1000 if attendance.distance else 'None'
            if isinstance(distance_meters, float):
                distance_meters = f"{distance_meters:.2f}"

            # Format the date in YYYY-MM-DD format
            formatted_date = attendance.date.strftime('%Y-%m-%d') if attendance.date else 'None'
            formatted_first_in = attendance.first_in.strftime('%H:%M:%S') if attendance.first_in else 'None'
            formatted_last_out = attendance.last_out.strftime('%H:%M:%S') if attendance.last_out else 'None'

            row = [
                attendance.user.username,
                attendance.user.first_name,
                attendance.user.last_name,
                attendance.user.email,
                formatted_date,
                formatted_first_in,
                formatted_last_out,
                f"{distance_meters} m",
            ]
            for col_num, cell_value in enumerate(row, 1):
                cell = worksheet.cell(row=row_num, column=col_num)
                cell.value = cell_value

        # Save the workbook to the HTTP response
        workbook.save(response)
        return response

class LeaveNew (LoginRequiredMixin,CreateView, ListView):
    model = Leave
    template_name = 'hrms/leave/create.html'
    form_class = LeaveForm
    login_url = 'hrms:login'
    success_url = reverse_lazy('hrms:leave_new')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["leaves"] = Leave.objects.all()
        return context

class Payroll(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'hrms/payroll/index.html'
    login_url = 'hrms:login'
    context_object_name = 'stfpay'

class RecruitmentNew (CreateView):
    model = Recruitment
    template_name = 'hrms/recruitment/index.html'
    form_class = RecruitmentForm
    success_url = reverse_lazy('hrms:recruitment')

class RecruitmentAll(LoginRequiredMixin,ListView):
    model = Recruitment
    login_url = 'hrms:login'
    template_name = 'hrms/recruitment/all.html'
    context_object_name = 'recruit'

class RecruitmentDelete (LoginRequiredMixin,View):
    login_url = 'hrms:login'
    def get (self, request,pk):
     form_app = Recruitment.objects.get(pk=pk)
     form_app.delete()
     return redirect('hrms:recruitmentall', permanent=True)

class Pay(LoginRequiredMixin,ListView):
    model = Employee
    template_name = 'hrms/payroll/index.html'
    context_object_name = 'emps'
    login_url = 'hrms:login'
