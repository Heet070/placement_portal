import csv
import json
import os
import io
import zipfile
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Count, Q, Avg, Sum
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt

# We might not have Anthropic installed yet or configured, handling it gracefully
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from .models import Drive, Student, Company, Profile, Branch
from .decorators import login_required
from .forms import (
    DriveStep1Form, BranchSelectionForm, StudentForm, 
    CompanyForm, ProfileForm, CSVUploadForm, BranchForm, EditDriveForm
)

@login_required
def dashboard(request):
    """Stats cards + chart data per drive"""
    active_drives = Drive.objects.filter(status='active')
    
    drive_stats = []
    for d in active_drives:
        drive_stats.append({
            'drive': d,
            'total_students': d.students.count(),
            'placed_students': d.students.exclude(placement_status='Unplaced').count(),
            'total_companies': d.companies.count()
        })
    
    context = {
        'drive_stats': drive_stats,
    }
    return render(request, 'portal/dashboard.html', context)


@login_required
def drives_list(request):
    """All drives table"""
    drives = Drive.objects.all()
    branches = Branch.objects.all()
    return render(request, 'portal/drives.html', {'drives': drives, 'branches': branches})


@login_required
def create_drive_step1(request):
    if request.method == 'POST':
        form = DriveStep1Form(request.POST)
        if form.is_valid():
            drive = form.save(commit=False)
            try:
                drive.clean()
                drive.save()
                request.session['latest_drive_id'] = drive.drive_id
                return redirect('create_drive_step2')
            except ValidationError as e:
                messages.error(request, e.message)
    else:
        form = DriveStep1Form()
    return render(request, 'portal/create_drive_step1.html', {'form': form})


@login_required
def create_drive_step2(request):
    drive_id = request.session.get('latest_drive_id')
    if drive_id:
        latest_drive = Drive.objects.filter(pk=drive_id).first()
    else:
        latest_drive = Drive.objects.order_by('-drive_year').first()
        
    if not latest_drive:
        return redirect('create_drive_step1')
        
    if request.method == 'POST':
        form = BranchSelectionForm(request.POST)
        if form.is_valid():
            branches = form.cleaned_data['branches']
            latest_drive.branches.set(branches)
            messages.success(request, 'Drive created successfully!')
            return redirect('drives')
    else:
        form = BranchSelectionForm()
    return render(request, 'portal/create_drive_step2.html', {'form': form, 'drive': latest_drive})


@login_required
def toggle_drive_status(request, drive_id):
    if request.method == 'POST':
        drive = get_object_or_404(Drive, pk=drive_id)
        if drive.status == 'active':
            drive.status = 'inactive'
            drive.save()
            messages.success(request, f'Drive {drive.drive_name} deactivated (archived).')
        else:
            try:
                drive.status = 'active'
                drive.clean()
                drive.save()
                messages.success(request, f'Drive {drive.drive_name} activated.')
            except ValidationError as e:
                messages.error(request, e.message)
    return redirect('drives')


@login_required
def edit_drive(request, drive_id):
    drive = get_object_or_404(Drive, pk=drive_id)
    if request.method == 'POST':
        form = EditDriveForm(request.POST, instance=drive)
        if form.is_valid():
            try:
                f = form.save(commit=False)
                f.clean()
                f.save()
                form.save_m2m()
                messages.success(request, 'Drive updated successfully.')
            except ValidationError as e:
                messages.error(request, e.message)
        else:
            for error in form.errors.values():
                messages.error(request, str(error))
        return redirect('drives')
    # Can also render a dedicated edit page or modal

@login_required
def delete_drive(request, drive_id):
    if request.method == 'POST':
        drive = get_object_or_404(Drive, pk=drive_id)
        drive_name = drive.drive_name
        drive.delete()
        messages.success(request, f'Drive {drive_name} deleted completely.')
    return redirect('drives')

@login_required
def export_drive_data(request, drive_id):
    drive = get_object_or_404(Drive, pk=drive_id)
    
    # 1. Create Students CSV
    student_output = io.StringIO()
    student_writer = csv.writer(student_output)
    student_writer.writerow(['ID', 'Name', 'Branch', 'CPI', 'Placement Status', 'Company', 'Profile', 'CTC', 'Stipend'])
    
    students = Student.all_objects.filter(drive=drive)
    for std in students:
        student_writer.writerow([
            std.student_id, std.std_name, std.branch.branch_name, 
            std.cpi, std.placement_status, 
            std.company.cmp_name if std.company else '', 
            std.profile.profile_name if std.profile else '',
            std.profile.ctc if std.profile else '',
            std.profile.stipend if std.profile else ''
        ])
    
    # 2. Create Companies CSV
    company_output = io.StringIO()
    company_writer = csv.writer(company_output)
    company_writer.writerow(['Company Name', 'Profile Name', 'CTC (LPA)', 'Stipend'])
    
    companies = Company.all_objects.filter(drive=drive).prefetch_related('profiles')
    for cmp in companies:
        if cmp.profiles.exists():
            for profile in cmp.profiles.all():
                company_writer.writerow([
                    cmp.cmp_name, profile.profile_name, profile.ctc, profile.stipend or ''
                ])
        else:
            company_writer.writerow([cmp.cmp_name, '', '', ''])

    # 3. Create ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('students.csv', student_output.getvalue())
        zip_file.writestr('companies.csv', company_output.getvalue())

    # 4. Return HttpResponse
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{drive.drive_id}_export.zip"'
    return response


@login_required
def students_list(request):
    students = Student.objects.all()
    
    # Apply filters if any
    drive_id = request.GET.get('drive')
    branch_ids = request.GET.getlist('branch')
    placement_status = request.GET.get('placement_status')
    search_query = request.GET.get('search')
    cpi_min = request.GET.get('cpi_min')
    cpi_max = request.GET.get('cpi_max')
    profile_id = request.GET.get('profile')
    
    if profile_id:
        students = students.filter(profile_id=profile_id)
    if drive_id:
        students = students.filter(drive_id=drive_id)
    if branch_ids:
        clean_branches = [b for b in branch_ids if b]
        if clean_branches:
            students = students.filter(branch_id__in=clean_branches)
    if placement_status:
        students = students.filter(placement_status=placement_status)
    if search_query:
        # Search by student ID or Name
        from django.db.models import Q
        students = students.filter(
            Q(student_id__icontains=search_query) | 
            Q(std_name__icontains=search_query)
        )
    if cpi_min:
        try:
            students = students.filter(cpi__gte=float(cpi_min))
        except ValueError:
            pass
    if cpi_max:
        try:
            students = students.filter(cpi__lte=float(cpi_max))
        except ValueError:
            pass
            
    # Sort by Student ID
    students = students.order_by('student_id')
        
    paginator = Paginator(students, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
        
    context = {
        'students': page_obj,
        'drives': Drive.objects.filter(status='active'),
        'branches': Branch.objects.all(),
        'companies': Company.objects.all(),
        'profiles': Profile.objects.all(),
        'student_form': StudentForm(),
        'csv_form': CSVUploadForm(),
        'branch_form': BranchForm(),
        'selected_branches': branch_ids,
        'filter_string': query_params.urlencode()
    }
    return render(request, 'portal/students.html', context)


@login_required
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student added successfully.')
        else:
            for error in form.errors.values():
                messages.error(request, str(error))
    return redirect('students')


@login_required
def add_branch(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Branch added successfully.')
        else:
            for error in form.errors.values():
                messages.error(request, str(error))
    return redirect(request.META.get('HTTP_REFERER', 'branches'))

@login_required
def branches_list(request):
    """View all branches."""
    branches = Branch.objects.all()
    branch_form = BranchForm()
    return render(request, 'portal/branches.html', {'branches': branches, 'branch_form': branch_form})

@login_required
def edit_branch(request, branch_id):
    """Edit branch details."""
    branch = get_object_or_404(Branch, pk=branch_id)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Branch updated successfully.')
        else:
            for error in form.errors.values():
                messages.error(request, str(error))
    return redirect('branches')

@login_required
def delete_branch(request, branch_id):
    """Delete a branch if no students are tied to it."""
    branch = get_object_or_404(Branch, pk=branch_id)
    if request.method == 'POST':
        try:
            branch.delete()
            messages.success(request, 'Branch deleted successfully.')
        except Exception as e:
            messages.error(request, 'Cannot delete this branch. Make sure no students or drives are actively using it.')
    return redirect('branches')


@login_required
def bulk_upload_students(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)
                count = 0
                with transaction.atomic():
                    for row_idx, row in enumerate(reader, start=2):
                        try:
                            branch_id = row['branch_id']
                            try:
                                branch = Branch.objects.get(branch_id=branch_id)
                            except Branch.DoesNotExist:
                                raise ValueError(f"Branch '{branch_id}' does not exist. Please create it first.")
                            
                            drive_id = row['drive_id']
                            try:
                                drive = Drive.objects.get(drive_id=drive_id)
                            except Drive.DoesNotExist:
                                raise ValueError(f"Drive '{drive_id}' does not exist. Please create it first.")

                            placement_status = row.get('placement_status', 'Unplaced')
                            if drive_id.startswith('PD') and placement_status not in ['Unplaced', 'Placed', 'PPO']:
                                raise ValueError(f"Invalid placement_status '{placement_status}' for PD drive.")
                            if drive_id.startswith('SI') and placement_status not in ['Unplaced', 'Summer Internship']:
                                raise ValueError(f"Invalid placement_status '{placement_status}' for SI drive.")

                            student = Student(
                                student_id=row['student_id'],
                                std_name=row['std_name'],
                                branch=branch,
                                drive=drive,
                                cpi=row['cpi'],
                                placement_status=placement_status
                            )
                            student.full_clean()
                            student.save()
                            count += 1
                        except Exception as e:
                            raise Exception(f"Row {row_idx}: {str(e)}")
                messages.success(request, f'Successfully uploaded {count} students.')
            except Exception as e:
                messages.error(request, f'Error processing CSV - {str(e)}')
    return redirect('students')


@login_required
def download_csv_template(request):
    """Download a sample CSV template for bulk student upload."""
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_upload_template.csv"'

    writer = csv.writer(response)
    writer.writerow(['student_id', 'std_name', 'branch_id', 'drive_id', 'cpi', 'placement_status'])
    writer.writerow(['STU001', 'John Doe', 'BTECH_CSE', 'SI2025', '8.5', 'Unplaced'])
    writer.writerow(['STU002', 'Jane Smith', 'BTECH_EE', 'PD2025', '9.1', 'Placed'])

    return response


@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully.')
        else:
            for error in form.errors.values():
                messages.error(request, str(error))
    return redirect('students')


@login_required
def delete_student(request, student_id):
    if request.method == 'POST':
        student = get_object_or_404(Student, pk=student_id)
        name = student.std_name
        student.delete()
        messages.success(request, f'Student "{name}" deleted successfully.')
    return redirect('students')


@login_required
def export_students_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Branch', 'Drive', 'CPI', 'Placement Status', 'Company', 'CTC', 'Stipend'])
    
    for std in Student.objects.all():
        writer.writerow([
            std.student_id, std.std_name, std.branch.branch_name, 
            std.drive.drive_name, std.cpi, std.placement_status, 
            std.company.cmp_name if std.company else '', 
            std.profile.ctc if std.profile else '',
            std.profile.stipend if std.profile else ''
        ])
    return response


@login_required
def companies_list(request):
    companies = Company.objects.all()
    context = {
        'companies': companies,
        'drives': Drive.objects.filter(status='active'),
        'company_form': CompanyForm(),
        'profile_form': ProfileForm()
    }
    return render(request, 'portal/companies.html', context)


@login_required
def add_company(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company added successfully.')
    return redirect('companies')


@login_required
def edit_company(request, cmp_id):
    cmp = get_object_or_404(Company, pk=cmp_id)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=cmp)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company updated successfully.')
    return redirect('companies')


@login_required
def delete_company(request, cmp_id):
    if request.method == 'POST':
        cmp = get_object_or_404(Company, pk=cmp_id)
        cmp.delete()
        messages.success(request, 'Company deleted.')
    return redirect('companies')


@login_required
def add_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        cmp_id = request.POST.get('cmp_id')
        cmp = get_object_or_404(Company, pk=cmp_id)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.cmp = cmp
            profile.save()
            messages.success(request, 'Profile added successfully.')
    return redirect('companies')


@login_required
def edit_profile(request, profile_id):
    profile = get_object_or_404(Profile, pk=profile_id)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
    return redirect('companies')


@login_required
def delete_profile(request, profile_id):
    if request.method == 'POST':
        profile = get_object_or_404(Profile, pk=profile_id)
        profile.delete()
        messages.success(request, 'Profile deleted.')
    return redirect('companies')


@login_required
def analytics(request):
    drives = Drive.objects.filter(status='active').order_by('-drive_year')
    drive_stats = []
    for drive in drives:
        is_si = drive.drive_id.startswith('SI')
        students = Student.all_objects.filter(drive=drive)
        total    = students.count()
        placed   = students.filter(placement_status='Placed').count()
        ppo      = students.filter(placement_status='PPO').count()
        si       = students.filter(placement_status='Summer Internship').count()
        unplaced = students.filter(placement_status='Unplaced').count()

        # For CTC stats: SI drives use Summer Internship students; PD drives use Placed+PPO
        if is_si:
            ctc_qs = students.filter(placement_status='Summer Internship', profile__isnull=False).select_related('profile')
            primary_count = si
        else:
            ctc_qs = students.filter(placement_status__in=['Placed', 'PPO'], profile__isnull=False).select_related('profile')
            primary_count = placed + ppo

        ctcs = [float(s.profile.ctc) for s in ctc_qs if s.profile and s.profile.ctc]
        avg_ctc = round(sum(ctcs) / len(ctcs), 2) if ctcs else 0
        sorted_ctcs = sorted(ctcs)
        n = len(sorted_ctcs)
        median_ctc = round((sorted_ctcs[n//2-1]+sorted_ctcs[n//2])/2 if n%2==0 else sorted_ctcs[n//2], 2) if sorted_ctcs else 0
        highest_ctc = round(max(ctcs), 2) if ctcs else 0
        overall_pct = round(primary_count / total * 100, 1) if total else 0

        branch_data = []
        for branch in drive.branches.all().order_by('branch_name'):
            b_stu = students.filter(branch=branch)
            b_total = b_stu.count()
            b_placed = b_stu.filter(placement_status='Placed').count()
            b_ppo = b_stu.filter(placement_status='PPO').count()
            b_si = b_stu.filter(placement_status='Summer Internship').count()
            b_unplaced = b_stu.filter(placement_status='Unplaced').count()

            if is_si:
                b_ctc_qs = b_stu.filter(placement_status='Summer Internship', profile__isnull=False).select_related('profile')
                b_primary = b_si
            else:
                b_ctc_qs = b_stu.filter(placement_status__in=['Placed','PPO'], profile__isnull=False).select_related('profile')
                b_primary = b_placed + b_ppo

            b_ctcs = [float(s.profile.ctc) for s in b_ctc_qs if s.profile and s.profile.ctc]
            b_avg = round(sum(b_ctcs)/len(b_ctcs),2) if b_ctcs else 0
            b_sorted = sorted(b_ctcs)
            bn = len(b_sorted)
            b_median = round((b_sorted[bn//2-1]+b_sorted[bn//2])/2 if bn%2==0 else b_sorted[bn//2],2) if b_sorted else 0
            b_highest = round(max(b_ctcs),2) if b_ctcs else 0
            b_pct = round(b_primary / b_total * 100, 1) if b_total else 0

            branch_data.append({
                'branch_name': branch.branch_name, 'branch_id': branch.branch_id,
                'total': b_total, 'placed': b_placed, 'ppo': b_ppo,
                'si': b_si, 'unplaced': b_unplaced,
                'placed_total': b_placed + b_ppo,
                'primary_count': b_primary,
                'avg_ctc': b_avg, 'median_ctc': b_median, 'highest_ctc': b_highest,
                'placement_pct': b_pct,
            })

        drive_stats.append({
            'drive': drive, 'is_si': is_si,
            'total': total, 'placed': placed, 'ppo': ppo,
            'si': si, 'unplaced': unplaced,
            'placed_total': placed + ppo, 'primary_count': primary_count,
            'avg_ctc': avg_ctc, 'median_ctc': median_ctc, 'highest_ctc': highest_ctc,
            'overall_pct': overall_pct, 'branches': branch_data,
        })
    return render(request, 'portal/analytics.html', {'drive_stats': drive_stats})


@login_required
def archive(request):
    # Get all drives that are inactive
    archived_drives = Drive.objects.filter(status='inactive')
    context = {'archived_drives': archived_drives}
    return render(request, 'portal/archive.html', context)


@login_required
def restore_drive(request, drive_id):
    if request.method == 'POST':
        drive = get_object_or_404(Drive, pk=drive_id)
        try:
            drive.status = 'active'
            drive.clean()
            drive.save()
            messages.success(request, f'Drive {drive.drive_name} restored successfully.')
        except ValidationError as e:
            messages.error(request, e.message)
    return redirect('archive')


@login_required
def export_archive_csv(request, drive_id):
    drive = get_object_or_404(Drive, pk=drive_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="archive_{drive.drive_name}.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Branch', 'CPI', 'Placement Status', 'Company', 'CTC', 'Stipend'])
    
    # Bypass ActiveDriveManager for archive export
    students = Student.all_objects.filter(drive=drive)
    for std in students:
        writer.writerow([
            std.student_id, std.std_name, std.branch.branch_name, 
            std.cpi, std.placement_status, 
            std.company.cmp_name if std.company else '', 
            std.profile.ctc if std.profile else '',
            std.profile.stipend if std.profile else ''
        ])
    return response


@csrf_exempt
def rag_query(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query')
            
            # Aggregate stats
            total_students = Student.all_objects.count()
            placed_students = Student.all_objects.exclude(placement_status='Unplaced').count()
            
            context_str = f"Total Students: {total_students}. Placed: {placed_students}."
            
            # Simple RAG integration using anthropic if available
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if Anthropic and api_key:
                client = Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=500,
                    system="You are a helpful placement analytics assistant.",
                    messages=[
                        {"role": "user", "content": f"Context: {context_str}\n\nQuestion: {query}"}
                    ]
                )
                answer = response.content[0].text
            else:
                # Mock response if no key
                answer = f"I see your question: '{query}'. Based on my context, we have {total_students} total students and {placed_students} are placed. (Please configure ANTHROPIC_API_KEY for full AI responses)."
                
            return JsonResponse({'response': answer})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=400)


@login_required
def analytics_data(request):
    data = {}
    for d in Drive.objects.filter(status='active'):
        placed = d.students.filter(placement_status='Placed').count()
        ppo = d.students.filter(placement_status='PPO').count()
        si = d.students.filter(placement_status='Summer Internship').count()
        unplaced = d.students.filter(placement_status='Unplaced').count()
        
        labels = []
        counts = []
        colors = []
        
        if placed > 0:
            labels.append('Placed')
            counts.append(placed)
            colors.append('#28a745')
        if ppo > 0:
            labels.append('PPO')
            counts.append(ppo)
            colors.append('#17a2b8')
        if si > 0:
            labels.append('Summer Internship')
            counts.append(si)
            colors.append('#ffc107')
        if unplaced > 0 or len(labels) == 0:
            labels.append('Unplaced')
            counts.append(unplaced)
            colors.append('#dc3545')
        
        data[d.drive_id] = {
            'labels': labels,
            'datasets': [{
                'data': counts,
                'backgroundColor': colors
            }]
        }
        
    return JsonResponse({'overview': data})


@login_required
def get_profiles_for_drive(request, drive_id):
    profiles = Profile.objects.filter(cmp__drive_id=drive_id)
    return JsonResponse({'profiles': list(profiles.values('profile_id', 'profile_name', 'cmp__cmp_name'))})


@login_required
def get_profiles_for_company(request, cmp_id):
    profiles = Profile.objects.filter(cmp_id=cmp_id)
    return JsonResponse({'profiles': list(profiles.values('profile_id', 'profile_name', 'ctc', 'stipend'))})