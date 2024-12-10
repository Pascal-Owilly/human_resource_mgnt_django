from django.urls import path
from . import views
from .views_absent_satffes import AbsentStaffersView, download_excel, download_pdf
from .views_reset_imei import DeviceListView, reset_all_imeis, reset_single_imei
from contract_management import views as contract_management_views

app_name = 'hrms'

urlpatterns = [

# Authentication Routes
    path('', views.Index.as_view(), name='index'),
    path('register/', views.Register.as_view(), name='reg'),
    path('register/employees/', views.upload_file, name='employee_bulk_register'),
    path('register/account_manager/', views.AccountManager_New.as_view(), name='account_manager_register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.Logout_View.as_view(), name='logout'),
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('unauthorized/', views.unauthorized, name='unauthorized'),
    path('assign-role/', views.assign_role, name='assign_role'),

# Users
    path('dashboard/user-list/', views.UserListView.as_view(), name='user_list'),
    path('dashboard/user-detail/<int:user_id>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/update/<int:pk>/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/archive/<int:pk>/', views.UserArchiveView.as_view(), name='user_archive'),
    path('users/archived/', views.ArchivedUserListView.as_view(), name='archived_user_list'),
    path('user_unarchive/<int:pk>/', views.UserUnarchiveView.as_view(), name='user_unarchive'),
    path('users/delete/<int:pk>/', views.UserDeleteView.as_view(), name='user_delete'),
    path('user/<int:id>/update-location/', views.update_user_location, name='update_user_location'),

# Admin routes
    path('dashboard/admin/', views.AdminDashboard.as_view(), name='admin_dashboard'),
    path('dashboard/admin-list/', views.AdminListView.as_view(), name='admin_list'),
    path('dashboard/admin/<int:pk>/view/', views.Admin_View.as_view(), name='admin_single_view'),

# Human resoource managers

    path('dashboard/human-resource/', views.HumanResourceManagerDashboard.as_view(), name='hr_dashboard'),
    path('dashboard/hr-manager/add/', views.HumanResourceManagerNew.as_view(), name='hr_add'),
    path('dashboard/hr-manager-list/', views.HumanResourceManagerAll.as_view(), name='hr_all'),
    path('dashboard/hr-manager/<int:pk>/view/', views.HumanResourceManagerView.as_view(), name='hr_single_view'),


# Account managers

    path('dashboard/account-manager/', views.AccountManagerDashboard.as_view(), name='account_manager_dashboard'),
    path('dashboard/account-manager-list/', views.Account_Manager_All.as_view(), name='account_manager_all'),
    path('dashboard/account-manager/<int:pk>/view/', views.Account_Manager_View.as_view(), name='account_manager_single_view'),

# For specific clients & employee attendance
    path('dashboard/account/manager/clients/', views.AccountManagerClientListView.as_view(), name='account_manager_clients'),
    path('dashboard/account-manager-attendance-list/', views.Attendance_Account_Manager.as_view(), name='account_manager_attendance_list'),

# Employee Routes
    path('dashboard/employee/', views.EmployeeDashboard.as_view(), name='employee_dashboard'),
    path('dashboard/employee/all', views.Employee_All.as_view(), name='employee_all'),
    path('dashboard/employee/new/', views.Employee_New.as_view(), name='employee_new'),
    path('dashboard/employee/<int:pk>/view/', views.Employee_View.as_view(), name='employee_view'),
    path('dashboard/employee/<int:pk>/update/', views.Employee_Update.as_view(), name='employee_update'),
    path('dashboard/employee/<int:pk>/delete/', views.Employee_Delete.as_view(), name='employee_delete'),
    path('dashboard/employee/<int:id>/kin/add/', views.Employee_Kin_Add.as_view(), name='kin_add'),
    path('dashboard/employee/<int:id>/kin/<int:pk>/update/', views.Employee_Kin_Update.as_view(), name='kin_update'),

#Department Routes
    path('dashboard/department/all/', views.DepartmentListView.as_view(), name='depat_all'),
    path('dashboard/department/<int:pk>/', views.Department_Detail.as_view(), name='dept_detail'),
    path('dashboard/department/add/', views.Department_New.as_view(), name='dept_new'),
    path('dashboard/department/<int:pk>/update/', views.Department_Update.as_view(), name='dept_update'),

#Client Routes
    path('dashboard/client/all/', views.ClientListView.as_view(), name='clnt_all'),
    path('dashboard/client/<int:pk>/', views.Client_Detail.as_view(), name='clnt_detail'),
    path('dashboard/client/add/', views.Client_New.as_view(), name='clnt_new'),
    path('dashboard/client/<int:pk>/update/', views.Client_Update.as_view(), name='client_update'),

#Attendance Routes

    path('add-location/', views.AddLocationView.as_view(), name='add_location'),
    path('locations/', views.LocationListView.as_view(), name='location_list'),
    path('location/edit/<int:pk>/',  views.LocationUpdateView.as_view(), name='edit_location'),

    path('dashboard/attendance/in/admin/', views.Attendance_Admin.as_view(), name='attendance_new'),
    path('dashboard/attendance/emp/', views.Attendance_Employee.as_view(), name='attendance_employee'),
    path('dashboard/attendance/account-manager-list/', views.Attendance_Account_Manager.as_view(), name='attendance_account_manager_list'),

    path('dashboard/attendance/<int:pk>/out/', views.Attendance_Out.as_view(), name='attendance_out'),
    path('dashboard/attendance/<int:pk>/out_emp/', views.Attendance_Out_Emp.as_view(), name='attendance_out_emp'),
    path('dashboard/attendance/<int:pk>/out_acct_mng/', views.Attendance_Out_Account_Manager.as_view(), name='attendance_out_accnt_mng'),

    path('dashboard/attendance/clock_in/', views.ClockInView.as_view(), name='clock_in'),
    path('dashboard/attendance/clock_in_emp/', views.ClockInView.as_view(), name='clock_in_emp'),
    path('dashboard/attendance/clock_in_acct_mng/', views.ClockInView.as_view(), name='clock_in_acct_mng'),

    path('dashboard/absent-staffers/', AbsentStaffersView.as_view(), name='absent-staffers'),

    path('download_pdf/', views.DownloadPDF.as_view(), name='download_pdf'),
    path('download_excel/', views.DownloadExcel.as_view(), name='download_excel'),

    # Absent staffers
    path('dashboard/absent-staffers/', AbsentStaffersView.as_view(), name='absent_staffers'),
    path('dashboard/absent-staffers/download-excel/', download_excel, name='download_absent_staffers_excel'),
    path('dashboard/absent-staffers/download-pdf/', download_pdf, name='download_absent_staffers_pdf'),

    # RESET Imei
    path('devices/list', DeviceListView.as_view(), name='device_list'),  # URL for resetting a specific IMEI
    path('devices/reset-imei/<int:pk>/', reset_single_imei, name='reset_single_imei'),  # URL for resetting a specific IMEI
    path('devices/reset_all/', reset_all_imeis, name='reset_all_imeis'),  # URL for resetting all IMEIs

    
#Leave Routes

    path("dashboard/leave/new/", views.LeaveNew.as_view(), name="leave_new"),

#Recruitment

    path("recruitment/",views.RecruitmentNew.as_view(), name="recruitment"),
    path("recruitment/all/",views.RecruitmentAll.as_view(), name="recruitmentall"),
    path("recruitment/<int:pk>/delete/", views.RecruitmentDelete.as_view(), name="recruitmentdelete"),

#Payroll
    path("employee/pay/",views.Pay.as_view(), name="payroll"),

# contract_dashboard
    path('contracts-dashboard/', views.ContractDashboardView.as_view(), name='contract_dashboard'),
    path('upload_excel/', views.UploadExcelView.as_view(), name='upload_excel'),
    path('search/', views.SearchResultsView.as_view(), name='search_results'),
    path('contract/<int:contract_id>/', views.contract_detail, name='contract_detail'),
    # path('contract/sign/<int:contract_id>/', views.sign_contract, name='sign_contract'),
    path('download/sample-excel/', views.download_sample_excel, name='download_sample_excel'),

# CONTRACT MANAGEMENT   

  # Create a contract template

    path('contract_management/create-template/', contract_management_views.create_contract_template, name='create_contract_template'),
    path('contract_management/create-contract/<int:template_id>/', contract_management_views.create_contract, name='create_contract'),
    path('contract_management/bulk-upload/<int:template_id>/', contract_management_views.bulk_upload_contracts, name='bulk_upload_contracts'),
    path('contract_management/templates/', contract_management_views.combined_contract_and_template_list, name='template_list'),
    path('contract_management/contract-preview/<int:contract_id>/', contract_management_views.contract_preview, name='contract_preview'),
    path('user-search/', contract_management_views.user_search, name='user_search'),
    path('contract/<int:contract_id>/sign/', contract_management_views.sign_contract, name='sign_contract'),
    path('contract_management/sign-success/<int:contract_id>/', contract_management_views.contract_sign_success, name='contract_sign_success'),

    # privacy policy
    path('privacy-policy/', contract_management_views.privacy_policy, name='privacy_policy'),

    # New Contract bulk upload
    path('upload-bulk-excel/', contract_management_views.upload_contract_excel, name='upload_bulk_excel'),  # Upload Excel
    path('generate-bulk-contracts/', contract_management_views.generate_contracts, name='generate_contracts'),  # Generate Contracts
    path('create_bulk_template/', contract_management_views.create_bulk_contract_template, name='create_contract_bulk_template'),
    path('preview_bulk_contract/<int:template_id>/', contract_management_views.preview_bulk_contract, name='preview_bulk_contract'),
    # path('bulk_upload_contracts/<int:template_id>/', views.bulk_upload_contracts, name='bulk_upload_contracts'),
]   
    