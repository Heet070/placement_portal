from django.test import TestCase
from django.core.exceptions import ValidationError
from portal.models import Branch, Drive, Student, Company, Profile
from portal.forms import StudentForm


class StudentOfferLetterTests(TestCase):
    def setUp(self):
        # Create Branch
        self.branch = Branch.objects.create(
            branch_id="BTECH_CSE",
            branch_name="Computer Science"
        )
        # Create Drives
        self.active_pd_drive = Drive.objects.create(
            drive_id="PD2025",
            drive_name="Placement Drive 2025",
            drive_year=2025,
            status="active"
        )
        self.active_pd_drive.branches.add(self.branch)
        
        self.active_si_drive = Drive.objects.create(
            drive_id="SI2025",
            drive_name="Summer Internship 2025",
            drive_year=2025,
            status="active"
        )
        self.active_si_drive.branches.add(self.branch)

        # Create Company
        self.company = Company.objects.create(
            cmp_name="Google",
            drive=self.active_pd_drive
        )

        # Create Profile
        self.profile = Profile.objects.create(
            cmp=self.company,
            profile_name="Software Engineer",
            ctc=15.0,
            stipend=50000.0,
            offer_type="J"
        )

    def test_unplaced_student_cannot_have_offer_letter(self):
        # Model level validation
        student = Student(
            student_id="STU001",
            std_name="John Doe",
            branch=self.branch,
            drive=self.active_pd_drive,
            cpi=8.5,
            placement_status="Unplaced",
            offer_letter="https://drive.google.com/file/d/12345"
        )
        with self.assertRaises(ValidationError):
            student.full_clean()

    def test_placed_student_can_have_offer_letter(self):
        student = Student(
            student_id="STU001",
            std_name="John Doe",
            branch=self.branch,
            drive=self.active_pd_drive,
            cpi=8.5,
            placement_status="Placed",
            company=self.company,
            profile=self.profile,
            offer_letter="https://drive.google.com/file/d/12345"
        )
        # Should clean successfully
        student.full_clean()
        student.save()
        
        saved = Student.all_objects.get(pk="STU001")
        self.assertEqual(saved.offer_letter, "https://drive.google.com/file/d/12345")

    def test_form_clears_offer_letter_if_unplaced(self):
        # When sending Unplaced status, form should clear offer letter
        form_data = {
            'student_id': "STU002",
            'std_name': "Jane Smith",
            'branch': self.branch.branch_id,
            'drive': self.active_pd_drive.drive_id,
            'cpi': 9.0,
            'placement_status': "Unplaced",
            'company': "",
            'profile': "",
            'offer_letter': "https://drive.google.com/file/d/12345"
        }
        form = StudentForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['offer_letter'], "")

    def test_form_retains_offer_letter_if_placed(self):
        form_data = {
            'student_id': "STU003",
            'std_name': "Bob Johnson",
            'branch': self.branch.branch_id,
            'drive': self.active_pd_drive.drive_id,
            'cpi': 7.5,
            'placement_status': "Placed",
            'company': self.company.cmp_id,
            'profile': self.profile.profile_id,
            'offer_letter': "https://drive.google.com/file/d/99999"
        }
        form = StudentForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['offer_letter'], "https://drive.google.com/file/d/99999")


class ProfileBranchTests(TestCase):
    def setUp(self):
        self.branch_cse = Branch.objects.create(
            branch_id="BTECH_CSE",
            branch_name="Computer Science"
        )
        self.branch_ece = Branch.objects.create(
            branch_id="BTECH_ECE",
            branch_name="Electronics"
        )
        self.active_drive = Drive.objects.create(
            drive_id="PD2025",
            drive_name="Placement Drive 2025",
            drive_year=2025,
            status="active"
        )
        self.active_drive.branches.add(self.branch_cse, self.branch_ece)

        self.company = Company.objects.create(
            cmp_name="Meta",
            drive=self.active_drive
        )

    def test_profile_can_have_multiple_branches(self):
        profile = Profile.objects.create(
            cmp=self.company,
            profile_name="Product Manager",
            ctc=20.0
        )
        profile.branches.add(self.branch_cse, self.branch_ece)
        
        self.assertEqual(profile.branches.count(), 2)
        self.assertIn(self.branch_cse, profile.branches.all())
        self.assertIn(self.branch_ece, profile.branches.all())


class ProfileOfferTypeValidationTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            branch_id="BTECH_CSE",
            branch_name="Computer Science"
        )
        self.si_drive = Drive.objects.create(
            drive_id="SI2025",
            drive_name="Summer Internship 2025",
            drive_year=2025,
            status="active"
        )
        self.si_drive.branches.add(self.branch)
        
        self.pd_drive = Drive.objects.create(
            drive_id="PD2025",
            drive_name="Placement Drive 2025",
            drive_year=2025,
            status="active"
        )
        self.pd_drive.branches.add(self.branch)

        self.si_company = Company.objects.create(
            cmp_name="Google SI",
            drive=self.si_drive
        )
        self.pd_company = Company.objects.create(
            cmp_name="Google PD",
            drive=self.pd_drive
        )

    def test_si_drive_only_allows_si_offer_type(self):
        # Invalid offer type J in SI drive
        profile_invalid = Profile(
            cmp=self.si_company,
            profile_name="SWE Intern",
            ctc=12.0,
            offer_type="J"
        )
        with self.assertRaises(ValidationError):
            profile_invalid.full_clean()

        # Valid offer type SI in SI drive
        profile_valid = Profile(
            cmp=self.si_company,
            profile_name="SWE Intern",
            ctc=12.0,
            offer_type="SI"
        )
        profile_valid.full_clean()  # Should not raise any error

    def test_pd_drive_does_not_allow_si_offer_type(self):
        # Invalid offer type SI in PD drive
        profile_invalid = Profile(
            cmp=self.pd_company,
            profile_name="Full Time SWE",
            ctc=25.0,
            offer_type="SI"
        )
        with self.assertRaises(ValidationError):
            profile_invalid.full_clean()

        # Valid offer type J in PD drive
        profile_valid = Profile(
            cmp=self.pd_company,
            profile_name="Full Time SWE",
            ctc=25.0,
            offer_type="J"
        )
        profile_valid.full_clean()  # Should not raise any error


