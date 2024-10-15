from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Device  # Ensure this imports your Device model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

@method_decorator(csrf_exempt, name='dispatch')
class DeviceListView(View):
    template_name = 'hrms/attendance/device_list.html'  # Change to your template path
    paginate_by = 25  # Number of devices per page

    def get(self, request):
        search_query = request.GET.get('search', '')

        # Constructing query based on search input
        devices_list = Device.objects.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(imei__icontains=search_query)  # Searching by IMEI as well
        ).order_by('-id')

        paginator = Paginator(devices_list, self.paginate_by)
        page_number = request.GET.get('page')

        try:
            devices = paginator.page(page_number)
        except PageNotAnInteger:
            devices = paginator.page(1)
        except EmptyPage:
            devices = paginator.page(paginator.num_pages)

        # Prepare device data for rendering
        devices_data = [
            {
                'id': device.id,
                'first_name': device.user.first_name if device.user else 'Unknown',
                'last_name': device.user.last_name if device.user else 'Unknown',
                'phone_number': device.user.phone_number if device.user else 'None',
                'email': device.user.email if device.user else 'Unknown',
                'imei': device.imei,
            }
            for device in devices
        ]

        return render(request, self.template_name, {'devices': devices_data, 'search_query': search_query})

    def post(self, request, pk):
        # Resetting the IMEI for a specific device
        device = get_object_or_404(Device, pk=pk)
        device.imei = ''  # Or set it to a default value if needed
        device.save()
    
        messages.success(request, f"IMEI for {device.user.first_name if device.user else 'Unknown'} has been reset successfully.")
        return redirect('hrms:device_list')  # Redirect to the device list page

def reset_all_imeis(request):
    if request.method == 'POST':
        # Resetting all IMEI numbers
        devices = Device.objects.all()
        for device in devices:
            device.imei = ''  # Or set it to a default value if needed
            device.save()

        messages.success(request, "All IMEI numbers have been reset successfully.")
        return redirect('hrms:device_list')  # Redirect to the device list page
    else:
        return redirect('hrms:device_list')

def reset_single_imei(request, pk):
    # Get the device based on the provided primary key (pk)
    device = get_object_or_404(Device, pk=pk)

    if request.method == 'POST':
        # Resetting the IMEI for the specified device
        device.imei = ''  # Or set it to a default value if needed
        device.save()

        messages.success(request, f"IMEI for {device.user.first_name if device.user else 'Unknown'} has been reset successfully.")
        return redirect('hrms:device_list')  # Redirect to the device list page

    # Render a confirmation template if not a POST request
    return render(request, 'hrms/attendance/reset_imei.html', {'device': device})
