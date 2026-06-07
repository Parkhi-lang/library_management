from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum

from .forms import LoginForm, StudentRegistrationForm, StudentProfileForm
from .models import CustomUser


def login_view(request):
    """
    Handles both GET (show empty form) and POST (validate and log in).
    One view handles both HTTP methods — this is standard Django pattern.
    We check request.method to know which branch to take.
    """

    # If already logged in, no reason to show the login page.
    # Prevents the back-button from showing the form to logged-in users.
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    if request.method == 'POST':
        # AuthenticationForm needs `request` as its first argument
        # (not just data=request.POST). This is AuthenticationForm's
        # specific interface — it uses the request for security checks.
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            # form.get_user() returns the authenticated user object.
            # This is only available after is_valid() succeeds.
            user = form.get_user()

            # login() does two things:
            # 1. Creates a session record in the database
            # 2. Sets a session cookie in the browser
            # Every subsequent request from this browser will include
            # that cookie, so Django knows who the user is.
            login(request, user)
            return redirect('accounts:role_redirect')
        else:
            messages.error(request, "Invalid username or password.")
            # messages.error() stores a message in the session.
            # The base template reads it and displays it.

    else:
        # GET request — just show a blank form
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def role_redirect(request):
    """
    A dedicated view whose only job is to route the user
    to the right dashboard based on their role.

    Why a separate view instead of redirecting inside login_view?
    Because other places in the app (like after registration)
    might also need to send users to the right dashboard.
    We only write this logic once.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    if request.user.is_librarian():
        return redirect('librarian:dashboard')
    else:
        return redirect('accounts:student_profile')


@login_required
# @login_required checks request.user.is_authenticated before running the view.
# If the user is NOT logged in, they're redirected to LOGIN_URL ('/accounts/login/').
# Without this decorator, any anonymous visitor could access the profile page.
def student_profile_view(request):
    """The student's own profile and dashboard."""

    # Role check: a librarian navigating to this URL should not see it.
    if not request.user.is_student():
        return redirect('librarian:dashboard')

    # Access profile via the related_name we defined on the OneToOneField.
    # This is a single DB query: SELECT * FROM studentprofile WHERE user_id = ...
    profile = request.user.student_profile

    # Import here to avoid circular imports at the top of the file.
    # `circulation` imports from `accounts`, so importing `circulation`
    # at module load time in `accounts` would create a circular dependency.
    from circulation.models import BorrowRecord

    # Filter only this student's unreturned books.
    # select_related('book') fetches the Book in the same SQL JOIN
    # so we don't hit the database again for each book in the template.
    borrowed_books = BorrowRecord.objects.filter(
        student=request.user,
        is_returned=False
    ).select_related('book')

    # aggregate(Sum(...)) runs: SELECT SUM(fine_amount) FROM ...
    # The result is a dict: {'total': Decimal('15.00')} or {'total': None}
    # `or 0` converts None (no records) to 0 so the template can display it safely.
    fine_data = BorrowRecord.objects.filter(
        student=request.user,
        fine_paid=False
    ).aggregate(total=Sum('fine_amount'))
    total_fine = fine_data['total'] or 0

    return render(request, 'accounts/student_profile.html', {
        'profile': profile,
        'borrowed_books': borrowed_books,
        'total_fine': total_fine,
    })


def logout_view(request):
    """
    logout() clears the session from the database AND
    clears the session cookie from the browser.
    After this, request.user becomes AnonymousUser.
    """
    logout(request)
    messages.success(request, "You've been logged out successfully.")
    return redirect('accounts:login')


def register_student(request):
    """
    Registration uses TWO forms submitted together:
    - StudentRegistrationForm: creates the CustomUser row
    - StudentProfileForm: creates the StudentProfile row

    Both must be valid before EITHER is saved.
    This ensures we never have a user without a profile (data integrity).
    """
    if request.method == 'POST':
        user_form    = StudentRegistrationForm(request.POST)
        profile_form = StudentProfileForm(request.POST)

        # Both must be valid. We call is_valid() on both separately
        # so we collect ALL errors at once, not just the first form's errors.
        user_form_valid    = user_form.is_valid()
        profile_form_valid = profile_form.is_valid()

        if user_form_valid and profile_form_valid:
            # commit=False gives us the model instance WITHOUT doing the
            # INSERT yet. We need to set the role and hash the password first.
            user = user_form.save(commit=False)

            # set_password() hashes the raw password using PBKDF2-SHA256
            # with a random salt. The hash is what gets stored in the database.
            # Django's authenticate() knows how to verify it.
            user.set_password(user_form.cleaned_data['password'])

            user.role = 'student'  # Force role — never trust form input for this
            user.save()            # Now the INSERT happens

            profile = profile_form.save(commit=False)
            profile.user = user    # Link to the user we just created
            profile.save()         # INSERT the profile row

            messages.success(request, "Account created successfully! Please log in.")
            return redirect('accounts:login')

    else:
        user_form    = StudentRegistrationForm()
        profile_form = StudentProfileForm()

    return render(request, 'accounts/register.html', {
        'user_form':    user_form,
        'profile_form': profile_form,
    })