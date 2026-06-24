from django.contrib import admin
from .models import Branch, Drive, Student, Company, Profile, InterviewRound, RoundStudent


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('branch_id', 'branch_name')
    search_fields = ('branch_name',)


@admin.register(Drive)
class DriveAdmin(admin.ModelAdmin):
    list_display = ('drive_id', 'drive_name', 'drive_year', 'status')
    list_filter = ('status', 'drive_year')
    search_fields = ('drive_name',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'std_name', 'branch', 'drive', 'cpi', 'placement_status', 'company')
    list_filter = ('placement_status', 'branch', 'drive')
    search_fields = ('std_name', 'company__cmp_name')

    def get_queryset(self, request):
        return Student.all_objects.all()


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('cmp_id', 'cmp_name', 'drive')
    list_filter = ('drive',)
    search_fields = ('cmp_name',)

    def get_queryset(self, request):
        return Company.all_objects.all()


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('profile_id', 'profile_name', 'cmp', 'ctc', 'stipend')
    list_filter = ('cmp',)
    search_fields = ('profile_name',)


@admin.register(InterviewRound)
class InterviewRoundAdmin(admin.ModelAdmin):
    list_display = ('round_id', 'round_name', 'profile', 'round_number', 'round_type', 'is_final')
    list_filter = ('round_type', 'is_final')
    search_fields = ('round_name', 'profile__profile_name')


@admin.register(RoundStudent)
class RoundStudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'round', 'student')
    search_fields = ('student__std_name', 'student__student_id', 'round__round_name')

