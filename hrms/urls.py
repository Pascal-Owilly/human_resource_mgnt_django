from django.urls import path
from . import views

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

# Users
    path('dashboard/user-list/', views.UserListView.as_view(), name='user_list'),
    path('dashboard/user-detail/<int:user_id>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/update/<int:pk>/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/archive/<int:pk>/', views.UserArchiveView.as_view(), name='user_archive'),
    path('users/archived/', views.ArchivedUserListView.as_view(), name='archived_user_list'),
    path('user_unarchive/<int:pk>/', views.UserUnarchiveView.as_view(), name='user_unarchive'),
    path('users/delete/<int:pk>/', views.UserDeleteView.as_view(), name='user_delete'),

# Admin routes
    path('dashboard/admin/', views.AdminDashboard.as_view(), name='admin_dashboard'),
    path('dashboard/admin-list/', views.AdminListView.as_view(), name='admin_list'),
    path('dashboard/admin/<int:pk>/view/', views.Admin_View.as_view(), name='admin_single_view'),

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
    path('dashboard/attendance/in/admin/', views.Attendance_Admin.as_view(), name='attendance_new'),
    path('dashboard/attendance/emp/', views.Attendance_Employee.as_view(), name='attendance_employee'),

    path('dashboard/attendance/<int:pk>/out/', views.Attendance_Out.as_view(), name='attendance_out'),
    path('dashboard/attendance/<int:pk>/out_emp/', views.Attendance_Out_Emp.as_view(), name='attendance_out_emp'),

    path('dashboard/attendance/clock_in/', views.AdminClockInView.as_view(), name='clock_in'),
    path('dashboard/attendance/clock_in_emp/', views.EmployeeClockInView.as_view(), name='clock_in_emp'),
    path('download_pdf/', views.DownloadPDF.as_view(), name='download_pdf'),
    path('download_excel/', views.DownloadExcel.as_view(), name='download_excel'),
#Leave Routes

    path("dashboard/leave/new/", views.LeaveNew.as_view(), name="leave_new"),

#Recruitment

    path("recruitment/",views.RecruitmentNew.as_view(), name="recruitment"),
    path("recruitment/all/",views.RecruitmentAll.as_view(), name="recruitmentall"),
    path("recruitment/<int:pk>/delete/", views.RecruitmentDelete.as_view(), name="recruitmentdelete"),

#Payroll
    path("employee/pay/",views.Pay.as_view(), name="payroll")

]
