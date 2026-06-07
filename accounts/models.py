from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    We extend AbstractUser, NOT AbstractBaseUser.
    AbstractUser already has: username, password, email,
    first_name, last_name, is_staff, is_active, date_joined.
    We get all that for free and just bolt on `role`.

    AbstractBaseUser would require us to rewrite everything from scratch.
    That's only needed if you want fundamentally different auth logic.
    """

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('librarian', 'Librarian'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='student',
        # default='student' is the safe fallback — a student cannot
        # accidentally get librarian access. Librarians are explicitly assigned.
    )

    # Helper methods let us write `user.is_librarian()` in templates
    # instead of `user.role == 'librarian'`. Cleaner and refactor-safe:
    # if we rename the role value later, we only change it here.
    def is_librarian(self):
        return self.role == 'librarian'

    def is_student(self):
        return self.role == 'student'

    def __str__(self):
        return f"{self.username} ({self.role})"


class StudentProfile(models.Model):
    """
    Student-specific data kept separate from CustomUser.
    Why separate? Because not all users are students.
    A librarian has no roll number or semester.
    Keeping them separate avoids nullable fields cluttering CustomUser.
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        # CASCADE: if the CustomUser row is deleted, this profile row
        # is automatically deleted too. No orphan records.
        related_name='student_profile',
        # related_name='student_profile' lets us write:
        #   user.student_profile  (from user → profile)
        # Without related_name, Django generates the ugly: user.studentprofile
    )

    roll_number = models.CharField(
        max_length=20,
        unique=True,
        # unique=True creates a UNIQUE constraint in the database.
        # Two students cannot have the same roll number — enforced at DB level,
        # not just in Python. DB-level constraints are always safer.
    )

    semester = models.IntegerField(
        choices=[(i, f'Semester {i}') for i in range(1, 9)],
        # List comprehension generates:
        # [(1,'Semester 1'), (2,'Semester 2'), ..., (8,'Semester 8')]
        # `choices` does two things: creates a dropdown in forms,
        # AND validates that the stored value is 1–8.
        default=1,
    )

    branch = models.CharField(max_length=50)  # e.g. "Computer Science"

    def __str__(self):
        return f"{self.user.get_full_name()} | {self.roll_number} | Sem {self.semester}"
        # get_full_name() is inherited from AbstractUser — returns "First Last"


class LibrarianProfile(models.Model):
    """
    Librarian-specific data. Same pattern as StudentProfile.
    Keeps librarian fields completely separate from student fields.
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='librarian_profile',
    )

    employee_id = models.CharField(max_length=20, unique=True)
    desk_number = models.CharField(max_length=10, blank=True)
    # blank=True: this field is optional. The form won't require it.
    # null is not needed here because CharField stores empty string for "no value".
    # For non-string fields (integers, dates), you'd need null=True as well.

    def __str__(self):
        return f"Librarian: {self.user.username} | EMP-{self.employee_id}"