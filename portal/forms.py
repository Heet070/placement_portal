from django import forms
from .models import Drive, Student, Company, Profile, Branch, InterviewRound


class DriveStep1Form(forms.ModelForm):
    """Step 1 of drive creation: basic details."""

    class Meta:
        model = Drive
        fields = ['drive_id', 'drive_name', 'drive_year', 'status']
        widgets = {
            'drive_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. SI2025, PD2025',
                'id': 'id_drive_id',
            }),
            'drive_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Campus Placement 2026',
                'id': 'id_drive_name',
            }),
            'drive_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2026',
                'id': 'id_drive_year',
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_status',
            }),
        }

class EditDriveForm(forms.ModelForm):
    """Form for editing drive including branches."""
    class Meta:
        model = Drive
        fields = ['drive_name', 'drive_year', 'status', 'branches']


class BranchSelectionForm(forms.Form):
    """Step 2 of drive creation: select branches."""
    branches = forms.ModelMultipleChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'branch-checkbox'}),
        required=True,
        error_messages={'required': 'Please select at least one branch.'},
    )


class StudentForm(forms.ModelForm):
    """Form for adding a single student."""

    class Meta:
        model = Student
        fields = ['student_id', 'std_name', 'branch', 'drive', 'cpi', 'placement_status', 'switch_app', 'company', 'profile', 'offer_letter']
        widgets = {
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student ID'}),
            'std_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student Name'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'drive': forms.Select(attrs={'class': 'form-control'}),
            'cpi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '10'}),
            'placement_status': forms.Select(attrs={'class': 'form-select'}),
            'switch_app': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'profile': forms.Select(attrs={'class': 'form-control'}),
            'offer_letter': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Google Drive Link'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active drives in dropdown
        self.fields['drive'].queryset = Drive.objects.filter(status='active')
        # Profile and company are optional initially, validated in clean
        self.fields['profile'].required = False
        self.fields['company'].required = False
        self.fields['offer_letter'].required = False
        # Filter profiles to active drive companies
        self.fields['profile'].queryset = Profile.objects.filter(cmp__drive__status='active')
        self.fields['company'].queryset = Company.objects.filter(drive__status='active')

    def clean(self):
        cleaned_data = super().clean()
        placement_status = cleaned_data.get('placement_status')
        company = cleaned_data.get('company')
        profile = cleaned_data.get('profile')
        offer_letter = cleaned_data.get('offer_letter')
        drive = cleaned_data.get('drive')

        # Drive-type restrictions
        if drive and placement_status:
            drive_id = str(drive.drive_id)
            if drive_id.startswith('SI') and placement_status not in ('Unplaced', 'Summer Internship'):
                self.add_error('placement_status',
                    'SI drives only allow "Unplaced" or "Summer Internship".')
            if drive_id.startswith('PD') and placement_status not in ('Unplaced', 'Placed', 'PPO'):
                self.add_error('placement_status',
                    'PD drives only allow "Unplaced", "Placed", or "PPO".')

        # Company & profile required when not unplaced
        if placement_status != 'Unplaced':
            if not company:
                self.add_error('company', 'Company is required when student is placed or has PPO/Internship.')
            if not profile:
                self.add_error('profile', 'Profile is required when student is placed or has PPO/Internship.')
        else:
            cleaned_data['company'] = None
            cleaned_data['profile'] = None
            cleaned_data['offer_letter'] = ''

        return cleaned_data


class CompanyForm(forms.ModelForm):
    """Form for adding a company."""

    class Meta:
        model = Company
        fields = ['cmp_name', 'drive']
        widgets = {
            'cmp_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'drive': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['drive'].queryset = Drive.objects.filter(status='active')


class ProfileForm(forms.ModelForm):
    """Form for adding a profile to a company."""
    branches = forms.ModelMultipleChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )

    class Meta:
        model = Profile
        fields = ['profile_name', 'ctc', 'stipend', 'offer_type', 'branches']
        widgets = {
            'profile_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Profile Name'}),
            'ctc': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'CTC in LPA'}),
            'stipend': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Stipend amount'}),
            'offer_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get('offer_type')
        
        cmp = None
        if self.instance and hasattr(self.instance, 'cmp') and self.instance.cmp:
            cmp = self.instance.cmp
        else:
            cmp_id = self.data.get('cmp_id')
            if cmp_id:
                try:
                    cmp = Company.objects.get(pk=cmp_id)
                except Company.DoesNotExist:
                    pass
        
        if cmp and offer_type:
            drive_id = str(cmp.drive_id)
            if drive_id.startswith('SI') and offer_type != 'SI':
                self.add_error('offer_type', 'Summer Internship drives (SI) only allow the "Summer Internship" (SI) offer type.')
            if drive_id.startswith('PD') and offer_type == 'SI':
                self.add_error('offer_type', 'Placement drives (PD) do not allow the "Summer Internship" (SI) offer type.')
                
        return cleaned_data


class CSVUploadForm(forms.Form):
    """Form for bulk CSV upload of students."""
    csv_file = forms.FileField(
        label='Upload CSV',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}),
    )

class BranchForm(forms.ModelForm):
    """Form for adding a new branch."""
    class Meta:
        model = Branch
        fields = ['branch_id', 'branch_name']
        widgets = {
            'branch_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BTECH_CSE'}),
            'branch_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Branch Name (e.g. Computer Science)'}),
        }


class InterviewRoundForm(forms.ModelForm):
    """Form for adding/editing an interview round."""
    class Meta:
        model = InterviewRound
        fields = ['round_name', 'round_type']
        widgets = {
            'round_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. OA Shortlist'}),
            'round_type': forms.Select(attrs={'class': 'form-select'}),
        }