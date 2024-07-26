# hrms/urls.py
from django.urls import path
from hrms import views_api

from .views_api import (
    UserListCreateAPIView,
    UserRetrieveUpdateDestroyAPIView,
    UserArchiveAPIView,
    UserUnarchiveAPIView,
    ArchivedUserListAPIView,
    UserDeleteAPIView,
    ClientListCreateAPIView,
    ClientRetrieveUpdateDestroyAPIView,
    EmployeeListCreateAPIView,
    EmployeeRetrieveUpdateDestroyAPIView,
    AdminClockInView,
    AdminClockInViewAll,
    CustomLoginView,
)

urlpatterns = [
    # Authentication
    path('login/',CustomLoginView.as_view(), name='custom_login'),
    path('password_reset/', views_api.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset_confirm/<uidb64>/<token>/', views_api.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password_reset_complete/', views_api.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('password_reset_done/', views_api.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('token/', views_api.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', views_api.MyTokenRefreshView.as_view(), name='token_refresh'),
    path('admin_register/', views_api.RegisterView.as_view(), name='admin_register'),
   
    # User URLs
    path('users/', UserListCreateAPIView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', UserRetrieveUpdateDestroyAPIView.as_view(), name='user-retrieve-update-destroy'),
    path('users/<int:pk>/archive/', UserArchiveAPIView.as_view(), name='user-archive'),
    path('users/<int:pk>/unarchive/', UserUnarchiveAPIView.as_view(), name='user-unarchive'),
    path('users/archived/', ArchivedUserListAPIView.as_view(), name='archived-user-list'),
    path('users/<int:pk>/delete/', UserDeleteAPIView.as_view(), name='user-delete'),

    # Account manahgers
    
    path('account_managers/', views_api.AccountManagerCreateAPIView.as_view(), name='account_manager-list-create'),
    path('account_managers/<int:pk>/', views_api.AccounteManagerListView.as_view(), name='account_manager-retrieve-update-destroy'),
    
    # Client URLs
    path('clients/', ClientListCreateAPIView.as_view(), name='client-list-create'),
    path('clients/<int:id>/', views_api.ClientDetailAPIView.as_view(), name='client-detail'),

    path('clients/assigned-to-me/', views_api.ClientsAssignedToMeAPIView.as_view(), name='clients-assigned-to-me'),
    path('clients/<int:pk>/employees/', views_api.ClientEmployeesAPIView.as_view(), name='client-employees'),
    path('clients_employee/employee-clock-in/', views_api.AcEmployeeClockInView.as_view(), name='employee_manager-assigned-to-account_manager'),
    
    # Employee
    path('employees/', EmployeeListCreateAPIView.as_view(), name='employee-list-create'),
    path('employees/<int:pk>/', EmployeeRetrieveUpdateDestroyAPIView.as_view(), name='employee-retrieve-update-destroy'),
    
    # HRs
    path('hr-managers/', views_api.HumanResourceManagerListAPIView.as_view(), name='hr-manager-list'),
    path('hr-managers/create/', views_api.HumanResourceManagerCreateAPIView.as_view(), name='hr-manager-create'),
    
    # Attendance
    path('verify-otp/', views_api.SendOTPView.as_view(), name='send_otp'),
    path('admin_clock-in/', AdminClockInView.as_view(), name='admin_clock_in'),
    path('clock_in_all/', AdminClockInViewAll.as_view(), name='all_clockins'),
    # path('employee_clock-in/', AdminClockInView.as_view(), name='employee_clock_in'),
    
    # DOWNLOADS
    path('download-pdf/', views_api.DownloadPDF.as_view(), name='download_pdf'),
    path('download-excel/', views_api.DownloadExcel.as_view(), name='download_excel'),
    
    
]

