import io
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime
from django.http import HttpResponse
import pandas as pd
from io import BytesIO
from xhtml2pdf import pisa
from .models import Attendance, Employee  # Ensure Employee is the correct model name
from django.template.loader import get_template
from openpyxl import Workbook

class AbsentStaffersView(LoginRequiredMixin, View):
    login_url = 'hrms:login'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'human_resource_manager' and not request.user.is_superuser:
            return render(request, 'auth/unauthorized.html')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Get today's date
        today = timezone.localdate()

        # Get query parameters with default values set to today if not provided
        start_date = request.GET.get('start_date', str(today))  # Default to today's date
        end_date = request.GET.get('end_date', str(today))      # Default to today's date
        keyword = request.GET.get('keyword', '')

        # Retrieve attendance records marked as 'PRESENT' for the given date range
        present_staffers = Attendance.objects.filter(status='PRESENT')

        # Filter by date range if provided
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            present_staffers = present_staffers.filter(date__range=(start_date_obj, end_date_obj))
        except ValueError:
            pass  # If invalid date format is provided, skip the date range filtering

        # Retrieve all employees
        all_employees = Employee.objects.all()

        # Get the IDs of employees who are marked as present in the given range using 'user_id'
        present_employee_ids = present_staffers.values_list('user_id', flat=True)

        # Filter employees who do not have a 'PRESENT' attendance status in the date range (i.e., absent staff)
        absent_employees = all_employees.exclude(id__in=present_employee_ids)

        # Perform search if a keyword is provided

        if keyword:
            absent_employees = absent_employees.filter(
                Q(employee__username__icontains=keyword) |
                Q(employee__first_name__icontains=keyword) |
                Q(employee__last_name__icontains=keyword) |
                Q(employee__phone_number__icontains=keyword) |
                Q(employee__email__icontains=keyword) |
                Q(employee__username__icontains=keyword) |  
                Q(employee__client__name__icontains=keyword) | 
                Q(employee__assigned_location__name__icontains=keyword)  
            )

        # Pagination for absent staff
        paginator_absent = Paginator(absent_employees, 50)  # Show 50 records per page
        page_number_absent = request.GET.get('page_absent')
        page_obj_absent = paginator_absent.get_page(page_number_absent)

        context = {
            'today': today,
            'absent_staffers': page_obj_absent,
            'total_absent_count': absent_employees.count(),  # Total count of absent employees
            'start_date': start_date,
            'end_date': end_date,
            'keyword': keyword,
            'page_obj_absent': page_obj_absent,
        }

        return render(request, 'hrms/attendance/absent_staffers.html', context)


# DOWNLOADS

def download_excel(request):
    # Get the current date and date range from query parameters
    today = timezone.localdate()
    start_date = request.GET.get('start_date', str(today))
    end_date = request.GET.get('end_date', str(today))

    # Convert the date strings to datetime objects
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date_obj = today
        end_date_obj = today

    # Retrieve attendance records marked as 'PRESENT' for the given date range
    present_staffers = Attendance.objects.filter(status='PRESENT', date__range=(start_date_obj, end_date_obj))
    present_employee_ids = present_staffers.values_list('user_id', flat=True)

    # Retrieve absent employees based on the filtered present employee IDs
    absent_employees = Employee.objects.exclude(id__in=present_employee_ids)

    # Create an Excel workbook and worksheet
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Absent Staffers'

    # Define the header for the Excel file
    headers = ['Username', 'First Name', 'Last Name', 'Phone Number', 'Email', 'Client', 'Location']
    worksheet.append(headers)  # Adds the header row

    # Populate the worksheet with absent employees data
    for employee in absent_employees:
        worksheet.append([
            employee.employee.username,
            employee.employee.first_name,
            employee.employee.last_name,
            employee.employee.phone_number,
            employee.employee.email,
            employee.employee.client.name if employee.employee.client else 'Not Assigned',
            employee.employee.assigned_location.name if employee.employee.assigned_location else 'Not assigned'  # Adjusted this line
        ])

    # Set column widths for better readability
    worksheet.column_dimensions['A'].width = 20  # Username
    worksheet.column_dimensions['B'].width = 15  # First Name
    worksheet.column_dimensions['C'].width = 15  # Last Name
    worksheet.column_dimensions['D'].width = 20  # Phone Number
    worksheet.column_dimensions['E'].width = 30  # Email
    worksheet.column_dimensions['F'].width = 15  # Client
    worksheet.column_dimensions['G'].width = 20  # Location

    # Save the workbook to an in-memory file
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)  # Move the pointer to the start of the file

    # Create the HTTP response with the Excel file
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="absent_staffers_{start_date}_to_{end_date}.xlsx"'

    return response

def download_pdf(request):
    # Get today's date
    today = timezone.localdate()

    # Get query parameters with default values set to today if not provided
    start_date = request.GET.get('start_date', str(today))  # Default to today's date
    end_date = request.GET.get('end_date', str(today))      # Default to today's date

    # Retrieve attendance records marked as 'PRESENT' for the given date range
    present_staffers = Attendance.objects.filter(status='PRESENT')

    # Filter by date range if provided
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        present_staffers = present_staffers.filter(date__range=(start_date_obj, end_date_obj))
    except ValueError as e:
        # Log the error or provide feedback
        return HttpResponse(f'Invalid date format: {e}', status=400)

    # Get the IDs of employees who are marked as present in the given range using 'user_id'
    present_employee_ids = present_staffers.values_list('user_id', flat=True)

    # Filter employees who do not have a 'PRESENT' attendance status in the date range (i.e., absent staff)
    absent_employees = Employee.objects.exclude(id__in=present_employee_ids)

    # Prepare the context to include the date range
    context = {
        'absent_employees': absent_employees,
        'start_date': start_date_obj,
        'end_date': end_date_obj,
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="absent_staffers.pdf"'
    
    template = get_template('hrms/attendance/absent_staffers_pdf.html')  # Adjust path as needed
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    
    return response

