# hrms/views_api.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, Client, Employee, Admin, Attendance, AccountManager, HumanResourceManager
from .serializers import UserSerializer, ClientSerializer, EmployeeSerializer, AttendanceSerializer, LoginSerializer, UserRegistrationSerializer,  PasswordResetSerializer, PasswordResetConfirmSerializer, HumanResourceManagerSerializer, AccountManagerSerializer
from django.shortcuts import get_object_or_404
import string
import random

# EMAILS
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# clockin 
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from geopy.distance import geodesic
from .models import Attendance, Employee 

#Authentication
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView
from .forms import LoginForm 
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.views import View
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .serializers import LoginSerializer
from .models import User, Admin
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

class CustomPasswordResetView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
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
                'protocol': 'https' if request.is_secure() else 'http',
                'password_reset_url': f"{settings.PROTOCOL}://{settings.DOMAIN}/reset/{uidb64}/{token}/",
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'theme_color': '#fdeb3d',
                'secondary_color': '#773697',
            }
            self.send_mail(
                'auth/password_reset_subject.txt',
                'auth/send_password_reset_email.html',
                context,
                settings.DEFAULT_FROM_EMAIL,
                email,
                'auth/send_password_reset_email.html',
            )
            
            return Response({'message': 'Password reset email sent'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        subject = render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())
        body = render_to_string(email_template_name, context)
        html_body = render_to_string(html_email_template_name, context)
        send_mail(subject, body, from_email, [to_email], html_message=html_body)

class CustomPasswordResetConfirmView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            uidb64 = serializer.validated_data['uidb64']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            try:
                user_id = urlsafe_base64_decode(uidb64).decode()
                user = get_user_model().objects.get(pk=user_id)
            except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
                user = None
            if user is not None and default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return Response({'message': 'Password has been reset'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid token or user'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class CustomPasswordResetCompleteView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({'message': 'Password reset complete'}, status=status.HTTP_200_OK)

class CustomPasswordResetDoneView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({'message': 'Password reset email sent'}, status=status.HTTP_200_OK)

# Token Obtain Pair view for getting access and refresh tokens
class MyTokenObtainPairView(TokenObtainPairView):
    pass

# Token Refresh view for refreshing access tokens
class MyTokenRefreshView(TokenRefreshView):
    pass
    
def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

    
class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserRegistrationSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
        
class HumanResourceManagerCreateAPIView(generics.CreateAPIView):
    serializer_class = HumanResourceManagerSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hr_manager = serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

        # Generate uidb64 and token for password reset email
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Send password reset email
        self.send_password_reset_email(uidb64, token, user.email, user.first_name, user.last_name, user.username)

        # Create a new HumanResourceManager instance and associate the user with it
        HumanResourceManager.objects.create(human_resource_manager=user)

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserRegistrationSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

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
        

class HumanResourceManagerListView(generics.ListCreateAPIView):
    queryset = HumanResourceManager.objects.all()
    serializer_class = HumanResourceManagerSerializer

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        serializer.save(
            username=self.request.data['username'],  
            email=self.request.data['email'],
            first_name=self.request.data['first_name'],
            last_name=self.request.data['last_name']
        )

class AccountManagerCreateAPIView(generics.CreateAPIView):
    serializer_class = AccountManagerSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account_manager = serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

        # Generate uidb64 and token for password reset email
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Send password reset email
        self.send_password_reset_email(uidb64, token, user.email, user.first_name, user.last_name, user.username)

        # Create a new HumanResourceManager instance and associate the user with it
        HumanResourceManager.objects.create(human_resource_manager=user)

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserRegistrationSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

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
        

class AccounteManagerListView(generics.ListCreateAPIView):
    queryset = AccountManager.objects.all()
    serializer_class = AccountManagerSerializer

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        serializer.save(
            username=self.request.data['username'],  # Assuming 'username' is passed in the request data
            email=self.request.data['email'],
            first_name=self.request.data['first_name'],
            last_name=self.request.data['last_name']
        )

    
class CustomLoginView(APIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Logged in successfully',
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone_number': user.phone_number,
                'address': user.address,
                'role': user.role,
                'clockin_privileges': user.clockin_privileges,
                'token': str(refresh.access_token),
                # Include other fields as needed
            })
        return Response({'error': 'Invalid credentials'}, status=400)  # Return error message for invalid credentials


class UserListCreateAPIView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
class UserUpdateAPIView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserArchiveAPIView(APIView):
    def post(self, request, pk):
        user = User.objects.get(pk=pk)
        user.is_archived = True
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class UserUnarchiveAPIView(APIView):
    def post(self, request, pk):
        user = User.objects.get(pk=pk)
        user.is_archived = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ArchivedUserListAPIView(generics.ListAPIView):
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.filter(is_archived=True).order_by('-id')

class UserDeleteAPIView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
# CLIENT
class ClientListCreateAPIView(generics.ListCreateAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class ClientRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    
class ClientsAssignedToMeAPIView(generics.ListAPIView):
    serializer_class = ClientSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        user = get_object_or_404(AccountManager, account_manager=self.request.user)
        return Client.objects.filter(account_manager=user)
        
        
from .serializers import ClientDetailSerializer

class ClientDetailAPIView(generics.RetrieveAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientDetailSerializer
    lookup_field = 'id'  
    
class ClientEmployeesAPIView(generics.ListAPIView):
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        client_id = self.kwargs['pk']
        return Employee.objects.filter(client_id=client_id)
        
# EMPLOYEE
class EmployeeListCreateAPIView(generics.ListCreateAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

class EmployeeRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    
from rest_framework import generics, status
from .serializers import HumanResourceManagerSerializer

class HumanResourceManagerListAPIView(generics.ListAPIView):
    queryset = HumanResourceManager.objects.all()
    serializer_class = HumanResourceManagerSerializer

class AcEmployeeClockInView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            # Retrieve the logged-in AccountManager instance
            account_manager = AccountManager.objects.get(id=request.user.id)

            # Fetch clients managed by the AccountManager
            managed_clients = Client.objects.filter(account_manager=account_manager)

            # Fetch employees whose user is linked to these clients
            employees = Employee.objects.filter(user__client__in=managed_clients)

            # Fetch clock-ins for these employees
            clock_ins = Attendance.objects.filter(staff__in=employees)

            # Serialize the clock-ins data
            serializer = AttendanceSerializer(clock_ins, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except AccountManager.DoesNotExist:
            return Response({'error': 'AccountManager not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        serializer = AttendanceSerializer(data=request.data)
        if serializer.is_valid():
            latitude = serializer.validated_data.get('latitude')
            longitude = serializer.validated_data.get('longitude')
            imei = serializer.validated_data.get('imei')

            # Ensure the user is authenticated
            if not request.user.is_authenticated:
                return Response({'error': 'User not authenticated.'}, status=status.HTTP_403_FORBIDDEN)

            try:
                # Retrieve the logged-in AccountManager instance
                account_manager = AccountManager.objects.get(id=request.user.id)

                # Fetch clients managed by the AccountManager
                managed_clients = Client.objects.filter(account_manager=account_manager)

                # Fetch employees whose user is linked to these clients
                employees = Employee.objects.filter(user__client__in=managed_clients)

                # Validate latitude and longitude
                try:
                    employee_location = (float(latitude), float(longitude))
                    geofence_center = (-1.2504447, 36.7150981)
                    distance_km = geodesic(employee_location, geofence_center).km
                except ValueError:
                    return Response({'error': 'Invalid latitude or longitude.'}, status=status.HTTP_400_BAD_REQUEST)

                # Check if the employee has the privilege to clock in from anywhere
                if request.user.clockin_privileges == User.CAN_CLOCK_IN_ANYWHERE:
                    response = self.clock_in(account_manager, latitude, longitude, distance_km, imei)
                    return response
                else:
                    # Check if the employee is within the geofence area
                    geofence_radius_km = 0.3  # 300 meters
                    if distance_km <= geofence_radius_km:
                        response = self.clock_in(account_manager, latitude, longitude, distance_km, imei)
                        return response
                    else:
                        return Response({'error': 'You are outside the allowed geofence area.'}, status=status.HTTP_403_FORBIDDEN)

            except AccountManager.DoesNotExist:
                return Response({'error': 'AccountManager not found.'}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def clock_in(self, account_manager, latitude, longitude, distance_km, imei):
        try:
            # Example: Creating a new Attendance instance
            clock_in_instance = Attendance.objects.create(
                account_manager=account_manager,
                latitude=latitude,
                longitude=longitude,
                distance_km=distance_km,
                imei=imei,
                clock_in_time=timezone.now()  # Adjust as per your requirements
            )
            return Response({'success': 'Clock-in successful.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
#OTP
from twilio.rest import Client
from .serializers import OTPSerializer

from decouple import config

# Twilio configuration
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER')
print('SID, AUTH token, phone', TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER)
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

class SendOTPView(APIView):
    def post(self, request):
        phone_number = request.data.get('phone_number')
        otp = generate_otp()  # Generate OTP 
        
        try:
            message = client.messages.create(
                body=f'Your OTP code is {otp}',
                from_=TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            # Store OTP in session or database for later verification
            store_otp(phone_number, otp)  # Implement this function as needed
            
            return Response({'message': 'OTP sent'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AdminClockInView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        imei = request.data.get('imei')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        # Check if latitude and longitude are provided
        if not latitude or not longitude:
            return Response({'error': 'Latitude and Longitude are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the user is authenticated
        if not request.user.is_authenticated:
            return Response({'error': 'User not authenticated.'}, status=status.HTTP_403_FORBIDDEN)

        user = request.user

        # Fetch user's assigned location
        location = user.assigned_location
        if not location:
            return Response({'error': 'User does not have an assigned location.'}, status=status.HTTP_400_BAD_REQUEST)

        geofence_center = (location.latitude, location.longitude)
        geofence_radius_km = location.radius

        try:
            admin_location = (float(latitude), float(longitude))
            distance_km = geodesic(admin_location, geofence_center).km
        except ValueError:
            return Response({'error': 'Invalid latitude or longitude.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check IMEI and handle clock-in
        if not imei:
            return Response({'error': 'IMEI is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the user is already clocked in today
        today_attendance = Attendance.objects.filter(user=user, date=timezone.localdate()).first()
        if today_attendance:
            if today_attendance.imei != imei:
                return Response({'error': 'IMEI mismatch. Please use the same device for clock-in.'}, status=status.HTTP_403_FORBIDDEN)
            else:
                # Clocking out
                self.clock_in(user, latitude, longitude, distance_km, imei)
                return Response({'message': 'Clock-out successful!'}, status=status.HTTP_200_OK)
        else:
            # Clocking in
            self.clock_in(user, latitude, longitude, distance_km, imei)
            return Response({'message': 'Clock-in successful!'}, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        attendances = Attendance.objects.filter(last_out__isnull=False).order_by('-id')
        serializer = AttendanceSerializer(attendances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def clock_in(self, user, latitude, longitude, distance_km, imei):
        today_attendance = Attendance.objects.filter(user=user, date=timezone.localdate(), last_out__isnull=True).first()
        if today_attendance:
            # Clocking out
            today_attendance.last_out = timezone.localtime()
            today_attendance.save()
            print(f'Clock-out successful! Latitude: {latitude}, Longitude: {longitude}. Distance from geofence center: {distance_km:.2f} km')
        else:
            # Clocking in
            Attendance.objects.create(
                user=user,
                name=f'{user.first_name} {user.last_name}',
                latitude=latitude,
                longitude=longitude,
                first_in=timezone.localtime(),
                imei=imei,
                status='PRESENT'
            )
            print(f'Clock-in successful! Latitude: {latitude}, Longitude: {longitude}. Distance from geofence center: {distance_km:.2f} km')

    def generate_otp():
        import random
        return str(random.randint(100000, 999999))

    def store_otp(phone_number, otp):
        # Implement this function to store OTP for later verification
        # e.g., store OTP in a cache or database with an expiry time
        pass

    def verify_otp(phone_number, otp):
        # Implement this function to verify OTP
        # e.g., check OTP against stored value and expiry time
        return True  # Replace with actual verification logic

    def send_late_arrival_notification(self, user, request):
        attendance_time = timezone.localtime()
        if attendance_time.time() > datetime.strptime('08:30', '%H:%M').time():
            subject = 'Late Clock-in Notification'
            html_message = render_to_string('hrms/employee/employee_late_arrival.html', {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'clock_in_time': attendance_time.strftime("%H:%M:%S")
            })
            plain_message = strip_tags(html_message)
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = 'pascalouma55@gmail.com'  # Adjust this to your recipient's email address

            send_mail(
                subject,
                plain_message,
                from_email,
                [to_email],
                html_message=html_message,
                fail_silently=True,
            )
            
# View all attendances
class AdminClockInViewAll(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = AttendanceSerializer(data=request.data)
        if serializer.is_valid():
            latitude = serializer.validated_data.get('latitude')
            longitude = serializer.validated_data.get('longitude')
            print(f"Received coordinates: latitude={latitude}, longitude={longitude}")
            
            # Ensure the user is authenticated
            if not request.user.is_authenticated:
                return Response({'error': 'User not authenticated.'}, status=status.HTTP_403_FORBIDDEN)

            # Retrieve the logged-in user instance (admin)
            user = request.user

            # Define the geofence center and radius
            geofence_center = (-1.2504447, 36.7150981)
            geofence_radius_km = 0.3  # 300 meters

            try:
                admin_location = (float(latitude), float(longitude))
                distance_km = geodesic(admin_location, geofence_center).km
                print(f"Calculated distance: {distance_km} km")
            except ValueError:
                return Response({'error': 'Invalid latitude or longitude.'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if the admin has the privilege to clock in from anywhere
            if request.user.clockin_privileges == User.CAN_CLOCK_IN_ANYWHERE:
                self.clock_in(user, latitude, longitude, distance_km)
                return Response({'message': 'Clock-in successful!'}, status=status.HTTP_200_OK)
            else:
                # Check if the admin is within the geofence area
                if distance_km <= geofence_radius_km:
                    self.clock_in(user, latitude, longitude, distance_km)
                    return Response({'message': 'Clock-in successful!'}, status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'You are outside the allowed geofence area.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    def get(self, request, *args, **kwargs):
        # Retrieve all clock-ins from the Attendance model
        attendances = Attendance.objects.filter(last_out__isnull=False).order_by('-id')
        serializer = AttendanceSerializer(attendances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def clock_in(self, user, latitude, longitude, distance_km):
        # Check if the admin is already clocked in today
        attendance = Attendance.objects.filter(user=user, date=timezone.localdate(), last_out__isnull=True).first()
        if attendance:
            # Clocking out
            attendance.last_out = timezone.localtime()
            attendance.save()
            print(f'Clock-out successful! Latitude: {latitude}, Longitude: {longitude}. Distance from geofence center: {distance_km:.2f} km')
        else:
            # Clocking in
            Attendance.objects.create(
                user=user,
                name=f'{user.first_name} {user.last_name}',
                latitude=latitude,
                longitude=longitude,
                first_in=timezone.localtime(),
                status='PRESENT'
            )
            print(f'Clock-in successful! Latitude: {latitude}, Longitude: {longitude}. Distance from geofence center: {distance_km:.2f} km')

    def send_late_arrival_notification(self, user, request):
        attendance_time = timezone.localtime()
        if attendance_time.time() > datetime.strptime('08:30', '%H:%M').time():
            subject = 'Late Clock-in Notification'
            html_message = render_to_string('hrms/employee/employee_late_arrival.html', {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'clock_in_time': attendance_time.strftime("%H:%M:%S")
            })
            plain_message = strip_tags(html_message)
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = 'pascalouma55@gmail.com'  # Adjust this to your recipient's email address

            send_mail(
                subject,
                plain_message,
                from_email,
                [to_email],
                html_message=html_message,
                fail_silently=True,
            )
            
from django.http import HttpResponse
from django.template.loader import get_template
from django.views import View
from django.utils import timezone
from django.db.models import Q
from .models import Attendance
from xhtml2pdf import pisa
import openpyxl

class DownloadPDF(View):
    def get(self, request, *args, **kwargs):
        date = request.GET.get('date', timezone.localdate())
        keyword = request.GET.get('keyword', '')

        attendances = Attendance.objects.filter(
            date=date
        )

        if keyword:
            attendances = attendances.filter(
                Q(user__first_name__icontains=keyword) |
                Q(user__last_name__icontains=keyword)
            )

        template = get_template('hrms/attendance/download_data/pdf_template.html')
        context = {
            'attendances': attendances,
            'date': date,
            'keyword': keyword,
        }
        html = template.render(context)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="attendance.pdf"'

        pisa_status = pisa.CreatePDF(
            html.encode('UTF-8'),
            dest=response,
        )

        if pisa_status.err:
            return HttpResponse('We had some errors with your request', status=500)
        return response

class DownloadExcel(View):
    def get(self, request, *args, **kwargs):
        date = request.GET.get('date', timezone.localdate())
        keyword = request.GET.get('keyword', '')

        attendances = Attendance.objects.filter(
            date=date
        )

        if keyword:
            attendances = attendances.filter(
                Q(user__first_name__icontains=keyword) |
                Q(user__last_name__icontains=keyword)
            )

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="attendance.xlsx"'

        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = 'Attendance'

        columns = ['Date', 'First-In (Arrival)', 'Last-Out (Departure)', 'Name', 'Distance (m)']
        row_num = 1

        for col_num, column_title in enumerate(columns, 1):
            cell = worksheet.cell(row=row_num, column=col_num)
            cell.value = column_title

        for attendance in attendances:
            row_num += 1
            admin_name = (
                f"{attendance.user.first_name} {attendance.user.last_name}"
                if attendance.user and attendance.user
                else 'N/A'
            )
            row = [
                attendance.date,
                attendance.first_in.strftime('%H:%M:%S') if attendance.first_in else '',
                attendance.last_out.strftime('%H:%M:%S') if attendance.last_out else '',
                admin_name,
                # You can add distance calculation here if needed
            ]
            for col_num, cell_value in enumerate(row, 1):
                cell = worksheet.cell(row=row_num, column=col_num)
                cell.value = cell_value

        workbook.save(response)
        return response
