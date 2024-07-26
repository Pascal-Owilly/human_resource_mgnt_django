from rest_framework import serializers
from .models import User, Client, Employee, Attendance, Admin, HumanResourceManager, AccountManager
from django.contrib.auth import authenticate, login

# Authentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            get_user_model().objects.get(email=value)
        except get_user_model().DoesNotExist:
            raise serializers.ValidationError('User with this email does not exist.')
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    uidb64 = serializers.CharField()
    token = serializers.CharField()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name')

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.is_superuser = True
        user.is_staff = True
        user.role = User.SUPERUSER
        user.save()
        Admin.objects.create(admin=user)
        return user
        
from rest_framework import serializers
from .models import User, HumanResourceManager, Client

class HumanResourceManagerSerializer(serializers.ModelSerializer):
    # Fields from User model
    username = serializers.CharField(source='human_resource_manager.username', required=True)
    email = serializers.EmailField(source='human_resource_manager.email', required=True)
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(source='human_resource_manager.first_name', required=True)
    last_name = serializers.CharField(source='human_resource_manager.last_name', required=True)
    phone_number = serializers.CharField(source='human_resource_manager.phone_number', required=False)
    address = serializers.CharField(source='human_resource_manager.address', required=False)
    emergency_contact = serializers.CharField(source='human_resource_manager.emergency_contact', required=False)
    gender = serializers.ChoiceField(choices=User.GENDER, source='human_resource_manager.gender', required=False)
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True, required=False)
    clockin_privileges = serializers.ChoiceField(choices=User.PRIVILEGE_CHOICES, source='human_resource_manager.clockin_privileges', required=False)

    class Meta:
        model = HumanResourceManager
        fields = ('username', 'email', 'password', 'first_name', 'last_name',
                  'phone_number', 'address', 'emergency_contact', 'gender',
                  'client', 'clockin_privileges')

    def create(self, validated_data):
        user_data = {
            'username': validated_data['human_resource_manager']['username'],
            'email': validated_data['human_resource_manager']['email'],
            'first_name': validated_data['human_resource_manager']['first_name'],
            'last_name': validated_data['human_resource_manager']['last_name'],
            'role': User.HUMAN_RESOURCE_MANAGER
        }
        password = validated_data.pop('password')
        client = validated_data.pop('client')

        # Create User instance
        user = User.objects.create_user(**user_data)
        user.set_password(password)
        user.save()

        # Create HumanResourceManager instance
        hr_manager = HumanResourceManager.objects.create(
            human_resource_manager=user,

            # Any other fields specific to HumanResourceManager
        )

        return hr_manager

class AccountManagerSerializer(serializers.ModelSerializer):
    # Fields from User model
    username = serializers.CharField(source='account_manager.username', required=True)
    email = serializers.EmailField(source='account_manager.email', required=True)
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(source='account_manager.first_name', required=True)
    last_name = serializers.CharField(source='account_manager.last_name', required=True)
    phone_number = serializers.CharField(source='account_manager.phone_number', required=False)
    address = serializers.CharField(source='account_manager.address', required=False)
    emergency_contact = serializers.CharField(source='account_manager.emergency_contact', required=False)
    gender = serializers.ChoiceField(choices=User.GENDER, source='account_manager.gender', required=False)
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True, required=False)
    clockin_privileges = serializers.ChoiceField(choices=User.PRIVILEGE_CHOICES, source='account_manager.clockin_privileges', required=False)

    class Meta:
        model = AccountManager
        fields = ('username', 'email', 'password', 'first_name', 'last_name',
                  'phone_number', 'address', 'emergency_contact', 'gender',
                  'client', 'clockin_privileges')

    def create(self, validated_data):
        user_data = {
            'username': validated_data['account_manager']['username'],
            'email': validated_data['account_manager']['email'],
            'first_name': validated_data['account_manager']['first_name'],
            'last_name': validated_data['account_manager']['last_name'],
            'role': User.ACCOUNT_MANAGER
        }
        password = validated_data.pop('password')
        client = validated_data.pop('client')

        # Create User instance
        user = User.objects.create_user(**user_data)
        user.set_password(password)
        user.save()

        # Create HumanResourceManager instance
        account_manager = AccountManager.objects.create(
            account_manager=user,
            client=client,
            # Any other fields specific to HumanResourceManager
        )

        return account_manager


        
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                data['user'] = user
            else:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError("Must include 'username' and 'password'.")

        return data
        
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User 
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number']

class AccountManagerSerializer(serializers.ModelSerializer):
    account_manager_user = UserSerializer(source='account_manager', read_only=True)  # Use source to specify the related field

    class Meta:
        model = AccountManager  
        fields = ['id', 'created_at', 'account_manager_user']  # Include 'account_manager_user' instead of 'account_manager'




class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'department', 'branch', 'account_manager', 'created_at']
        
      
from django.contrib.auth import get_user_model

class EmployeeSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='employee.username')
    email = serializers.ReadOnlyField(source='employee.email')
    first_name = serializers.ReadOnlyField(source='employee.first_name')
    last_name = serializers.ReadOnlyField(source='employee.last_name')
    phone_number = serializers.CharField(source='employee.phone_number')
    address = serializers.CharField(source='employee.address')
    emergency_contact = serializers.CharField(source='employee.emergency_contact')
    gender = serializers.ChoiceField(choices=User.GENDER, source='employee.gender')
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), source='employee.client')
    clockin_privileges = serializers.ChoiceField(choices=User.PRIVILEGE_CHOICES, source='employee.clockin_privileges')

    class Meta:
        model = Employee
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'address', 'emergency_contact', 'gender', 'client', 'clockin_privileges', 'created_at']
        
class ClientDetailSerializer(serializers.ModelSerializer):
    employees = EmployeeSerializer(many=True, read_only=True)

    account_manager = AccountManagerSerializer()

    class Meta:
        model = Client
        fields = ['id', 'name', 'department', 'branch', 'account_manager', 'created_at', 'employees']
        
from .models import HumanResourceManager

  
#Attendance
class AttendanceSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    
    def get_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return None
        
    class Meta:
        model = Attendance
        fields = '__all__'  
        
# OT[
class OTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6, required=False)  

