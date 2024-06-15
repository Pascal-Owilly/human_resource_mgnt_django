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

def process_uploaded_file(file_path):
    # Read Excel file
    df = pd.read_excel(file_path)

    # Iterate over rows and process employee data
    for index, row in df.iterrows():
        first_name = str(row.get('First Name', '')).strip()
        last_name = str(row.get('Last Name', '')).strip()
        email = str(row.get('Email', '')).strip()
        username = str(row.get('Username', '')).strip()
        mobile = str(row.get('Mobile', '')).strip()
        address = str(row.get('Address', '')).strip()
        emergency = str(row.get('Emergency', '')).strip()
        gender = str(row.get('Gender', '')).strip()
        thumb = row.get('Thumb')  # Ensure the 'Thumb' column is optional

        # Generate random password
        password = generate_random_password()

        # Create user account
        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            mobile=mobile,
            address=address,
            emergency=emergency,
            gender=gender,
            password=make_password(password),
            role=User.EMPLOYEE  

        )

        if pd.notnull(thumb):  # Check if thumb is not null
            thumb_file = ContentFile(thumb.encode())  # Assuming thumb is binary image data
            user.thumb.save(f'{username}_thumb.jpg', thumb_file)

        # Create an Employee instance and associate the user with it
        Employee.objects.create(employee=user)


        # Generate uidb64 and token for password reset email
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Send password reset email
        send_password_reset_email(user, uidb64, token)

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



