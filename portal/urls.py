from django.urls import path
from . import views
from . import auth_views

urlpatterns = [
    # ── Auth ──
    path('auth/login/', auth_views.login_view, name='admin_login'),
    path('auth/logout/', auth_views.logout_view, name='admin_logout'),
    path('auth/forgot-password/', auth_views.forgot_password_view, name='forgot_password'),
    path('auth/reset-password/<str:token>/', auth_views.reset_password_view, name='reset_password'),
    path('auth/change-password/', auth_views.change_own_password_view, name='change_own_password'),

    # ── Admin Management (super admin only) ──
    path('auth/admins/', auth_views.admin_management_view, name='admin_management'),
    path('auth/admins/create/', auth_views.create_admin_view, name='create_admin'),
    path('auth/edit-admin/<int:user_id>/', auth_views.edit_admin_view, name='edit_admin'),
    path('auth/delete-admin/<int:user_id>/', auth_views.delete_admin_view, name='delete_admin'),
    path('auth/resend-credentials/<int:user_id>/', auth_views.resend_credentials_view, name='resend_credentials'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Drives
    path('drives/', views.drives_list, name='drives'),
    path('drives/create/step1/', views.create_drive_step1, name='create_drive_step1'),
    path('drives/create/step2/', views.create_drive_step2, name='create_drive_step2'),
    path('drives/toggle/<str:drive_id>/', views.toggle_drive_status, name='toggle_drive_status'),
    path('drives/edit/<str:drive_id>/', views.edit_drive, name='edit_drive'),
    path('drives/delete/<str:drive_id>/', views.delete_drive, name='delete_drive'),
    path('drives/export/<str:drive_id>/', views.export_drive_data, name='export_drive_data'),

    # Students
    path('students/', views.students_list, name='students'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/bulk-upload/', views.bulk_upload_students, name='bulk_upload_students'),
    path('students/csv-template/', views.download_csv_template, name='download_csv_template'),
    path('students/edit/<str:student_id>/', views.edit_student, name='edit_student'),
    path('students/delete/<str:student_id>/', views.delete_student, name='delete_student'),
    path('students/export/', views.export_students_csv, name='export_students_csv'),
    path('branch/add/', views.add_branch, name='add_branch'),
    path('branches/', views.branches_list, name='branches'),
    path('branches/edit/<str:branch_id>/', views.edit_branch, name='edit_branch'),
    path('branches/delete/<str:branch_id>/', views.delete_branch, name='delete_branch'),

    # Companies
    path('companies/', views.companies_list, name='companies'),
    path('companies/add/', views.add_company, name='add_company'),
    path('companies/edit/<int:cmp_id>/', views.edit_company, name='edit_company'),
    path('companies/delete/<int:cmp_id>/', views.delete_company, name='delete_company'),

    # Profiles
    path('profiles/add/', views.add_profile, name='add_profile'),
    path('profiles/edit/<int:profile_id>/', views.edit_profile, name='edit_profile'),
    path('profiles/delete/<int:profile_id>/', views.delete_profile, name='delete_profile'),
    path('profiles/<int:profile_id>/rounds/', views.profile_rounds, name='profile_rounds'),
    path('profiles/<int:profile_id>/rounds/add/', views.add_round, name='add_round'),
    path('profiles/<int:profile_id>/rounds/reorder/', views.reorder_rounds, name='reorder_rounds'),
    path('profiles/<int:profile_id>/export-journey/', views.export_profile_journey_excel, name='export_profile_journey_excel'),
    path('rounds/<int:round_id>/edit/', views.edit_round, name='edit_round'),
    path('rounds/<int:round_id>/delete/', views.delete_round, name='delete_round'),
    path('rounds/<int:round_id>/upload-csv/', views.upload_round_students_csv, name='upload_round_students_csv'),
    path('rounds/<int:round_id>/add-student/', views.add_round_student, name='add_round_student'),
    path('rounds/<int:round_id>/remove-student/<str:student_id>/', views.remove_round_student, name='remove_round_student'),
    path('rounds/<int:round_id>/toggle-final/', views.toggle_round_final, name='toggle_round_final'),
    path('rounds/<int:round_id>/export/', views.export_round_students, name='export_round_students'),
    path('rounds/<int:round_id>/toggle-interview-shortlist/', views.toggle_interview_shortlist, name='toggle_interview_shortlist'),
    path('rounds/<int:round_id>/csv-template/', views.download_round_csv_template, name='download_round_csv_template'),

    # Student Detail
    path('students/<str:student_id>/detail/', views.student_detail, name='student_detail'),
    path('students/<str:student_id>/detail/export/', views.export_student_detail, name='export_student_detail'),


    # Analytics
    path('analytics/', views.analytics, name='analytics'),

    # Archive
    path('archive/', views.archive, name='archive'),
    path('archive/restore/<str:drive_id>/', views.restore_drive, name='restore_drive'),
    path('archive/export/<str:drive_id>/', views.export_archive_csv, name='export_archive_csv'),

    # API
    # path('api/rag-query/', views.rag_query, name='rag_query'),  # AI — disabled for now
    path('api/analytics-data/', views.analytics_data, name='analytics_data'),
    path('api/profiles/<str:drive_id>/', views.get_profiles_for_drive, name='get_profiles_for_drive'),
    path('api/profiles/company/<int:cmp_id>/', views.get_profiles_for_company, name='get_profiles_for_company'),
    path('generate-report/', views.text_to_sql_report, name='generate_report'),
]