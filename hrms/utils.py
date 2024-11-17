import pandas as pd
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from .models import User, Department
from django.contrib.auth.hashers import make_password
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
import os
from .models import Employee, User
from django.core.exceptions import ObjectDoesNotExist  # Add this line
from django.contrib import messages

def generate_random_password(length=12):
    letters = string.ascii_letters
    digits = string.digits
    symbols = string.punctuation
    all_characters = letters + digits + symbols
    password = ''.join(random.choice(all_characters) for i in range(length))
    return password

def send_password_reset_email(user, uidb64, token):
    reset_url = f"{settings.PROTOCOL}://{settings.DOMAIN}/reset/{uidb64}/{token}/"
    subject = 'Set Your Password'
    context = {
        'reset_url': reset_url,
        'theme_color': '#fdeb3d',
        'secondary_color': '#773697',
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
    }
    html_message = render_to_string('auth/password_reset_email.html', context)
    sender_email = settings.EMAIL_HOST_USER
    send_mail(subject, None, sender_email, [user.email], html_message=html_message)

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.contrib.auth.hashers import make_password
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages

def process_uploaded_file(request ,file):
    # Read Excel file
    df = pd.read_excel(file)

    messages.info(request, "Please be patient, uploading ...")

    results = []
    # Iterate over rows and process employee data
    for index, row in df.iterrows():
        first_name = str(row.get('First Name', '')).strip()
        last_name = str(row.get('Last Name', '')).strip()
        email = str(row.get('Email', '')).strip()
        username = str(row.get('Username', '')).strip()
        phone_number = str(row.get('Phone Number', '')).strip()
        address = str(row.get('Address', '')).strip()
        emergency_contact = str(row.get('Emergency Contact', '')).strip()
        gender = str(row.get('Gender', '')).strip()
        thumb = row.get('Thumb')  # 'Thumb' column is optional

        # Check if user with the same email or username already exists
        user_exists = False
        existing_user = User.objects.filter(username=username).first()
        if existing_user:
            results.append(f"User {username} already present. Proceeding to next user.")
            user_exists = True
        else:
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                results.append(f"User with email {email} already present. Proceeding to next user.")
                user_exists = True

        # Skip registration for existing users
        if user_exists:
            continue

        # Generate random password
        password = generate_random_password()

        # Create user account
        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            address=address,
            emergency_contact=emergency_contact,
            gender=gender,
            password=make_password(password),
            role=User.EMPLOYEE
        )

        # Process 'Thumb' if it's not empty
        if pd.notnull(thumb):
            thumb_file = ContentFile(thumb.encode())  # Assuming thumb is binary image data
            user.thumb.save(f'{username}_thumb.jpg', thumb_file)

        # Create an Employee instance and associate the user with it
        Employee.objects.create(employee=user)

        # Generate uidb64 and token for password reset email
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Send password reset email
        send_password_reset_email(user, uidb64, token)

    return results


# Attendance utility
from geopy.distance import geodesic

def is_within_geofence(employee_location, geofence_center, radius_km):
    """
    Check if the given employee location is within the geofence area.
    
    Args:
    - employee_location (tuple): (latitude, longitude) of the employee
    - geofence_center (tuple): (latitude, longitude) of the geofence center
    - radius_km (float): Radius of the geofence in kilometers

    Returns:
    - bool: True if within geofence, False otherwise
    """
    distance = geodesic(geofence_center, employee_location).km
    return distance <= radius_km


from datetime import timedelta
from django.utils import timezone
from .models import OTP

def generate_otp():
    return str(random.randint(100000, 999999))

def store_otp(user, otp):
    expiry_time = timezone.now() + timedelta(minutes=5)
    OTP.objects.update_or_create(user=user, defaults={'otp': otp, 'expiry_time': expiry_time})

def verify_otp(user, otp):
    try:
        otp_object = OTP.objects.get(user=user)
        return otp_object.otp == otp and otp_object.is_valid()
    except OTP.DoesNotExist:
        return False

# Contract
import PyPDF2

def parse_contract_document(file_path):
    # Open the PDF file
    with open(file_path, 'rb') as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""   
        for page in reader.pages:
            text += page.extract_text()

    # Extract details (this depends on the document structure)
    details = {}
    lines = text.splitlines()
    for line in lines:
        if "Email:" in line:
            details['email'] = line.split("Email:")[1].strip()
        if "First Name:" in line:
            details['first_name'] = line.split("First Name:")[1].strip()
        if "Last Name:" in line:
            details['last_name'] = line.split("Last Name:")[1].strip()
        if "Role:" in line:
            details['role'] = line.split("Role:")[1].strip()
        if "Position:" in line:
            details['position'] = line.split("Position:")[1].strip()
    
    return details


