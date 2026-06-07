from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from functools import wraps
import datetime

from .models import BorrowRecord
from books.models import Book


def librarian_required(view_func):
    """
    Custom decorator: login check + role check in one.
    Cleaner than chaining @login_required + @user_passes_test.
    """
    @wraps(view_func)
    # @wraps preserves the original function's name in tracebacks.
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_librarian():
            messages.error(request, "Access denied. Librarians only.")
            return redirect('accounts:student_profile')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def my_borrowed_books(request):
    """Student's active borrows + full history."""
    if request.user.is_librarian():
        return redirect('librarian:dashboard')

    active_borrows = BorrowRecord.objects.filter(
        student=request.user, is_returned=False
    ).select_related('book')
    # select_related('book'): fetches Book in same JOIN — prevents N+1 queries.

    past_borrows = BorrowRecord.objects.filter(
        student=request.user, is_returned=True
    ).select_related('book')
    # Django is lazy — these querysets don't hit DB until the template iterates them.

    unpaid_fine = BorrowRecord.objects.filter(
        student=request.user, fine_paid=False, fine_amount__gt=0
        # __gt = greater than. Only count records that actually have a fine.
    ).aggregate(total=Sum('fine_amount'))['total'] or 0

    return render(request, 'circulation/my_borrowed_books.html', {
        'active_borrows': active_borrows,
        'past_borrows':   past_borrows,
        'unpaid_fine':    unpaid_fine,
    })


@librarian_required
def issue_book(request):
    """Librarian issues a book: validate → create BorrowRecord → decrement copies."""

    if request.method == 'POST':
        roll_number = request.POST.get('roll_number', '').strip()
        isbn        = request.POST.get('isbn', '').strip()
        due_days    = int(request.POST.get('due_days', 14))

        from accounts.models import StudentProfile
        try:
            profile = StudentProfile.objects.get(roll_number=roll_number)
            student = profile.user
        except StudentProfile.DoesNotExist:
            messages.error(request, f"No student with roll number: {roll_number}")
            return redirect('circulation:issue_book')

        try:
            book = Book.objects.get(isbn=isbn)
        except Book.DoesNotExist:
            messages.error(request, f"No book with ISBN: {isbn}")
            return redirect('circulation:issue_book')

        if not book.is_available():
            messages.error(request, f'"{book.title}" has no available copies.')
            return redirect('circulation:issue_book')

        already_borrowed = BorrowRecord.objects.filter(
            student=student, book=book, is_returned=False
        ).exists()
        # .exists(): SELECT 1 LIMIT 1 — stops at first match. Faster than .count().

        if already_borrowed:
            messages.error(request, f"{student.get_full_name()} already has '{book.title}'.")
            return redirect('circulation:issue_book')

        due_date = datetime.date.today() + datetime.timedelta(days=due_days)
        # timedelta handles month/year boundaries correctly.

        BorrowRecord.objects.create(student=student, book=book, due_date=due_date)

        book.available_copies -= 1
        book.save(update_fields=['available_copies'])
        # update_fields: only UPDATE this one column, not the full row.

        messages.success(request, f'"{book.title}" issued to {student.get_full_name()}. Due: {due_date}')
        return redirect('circulation:issue_book')

    available_books = Book.objects.filter(available_copies__gt=0).order_by('title')
    return render(request, 'circulation/issue_book.html', {'available_books': available_books})


@librarian_required
def return_book(request, record_id):
    """Mark a borrow as returned, calculate fine, restore available copy."""

    record = get_object_or_404(BorrowRecord, id=record_id)
    # get_object_or_404: returns HTTP 404 if not found — proper error page, no crash.

    if record.is_returned:
        messages.warning(request, "This book has already been returned.")
        return redirect('librarian:dashboard')

    record.is_returned   = True
    record.returned_date = datetime.date.today()
    record.save(update_fields=['is_returned', 'returned_date'])

    record.calculate_fine()
    # calculate_fine() does its own save(update_fields=['fine_amount']) internally.

    book = record.book
    book.available_copies = min(book.available_copies + 1, book.total_copies)
    # min() prevents available_copies from exceeding total_copies (defensive).
    book.save(update_fields=['available_copies'])

    if record.fine_amount > 0:
        messages.success(request, f'"{book.title}" returned. Fine: ₹{record.fine_amount}')
    else:
        messages.success(request, f'"{book.title}" returned. No fine.')

    return redirect('librarian:dashboard')


@librarian_required
def all_borrow_records(request):
    """All records with filter: active / overdue / all."""

    filter_type = request.GET.get('filter', 'active')
    today = datetime.date.today()

    if filter_type == 'all':
        records = BorrowRecord.objects.all()
    elif filter_type == 'overdue':
        records = BorrowRecord.objects.filter(is_returned=False, due_date__lt=today)
        # due_date__lt = due_date < today → overdue
    else:
        records = BorrowRecord.objects.filter(is_returned=False)

    records = records.select_related('student', 'book', 'student__student_profile')
    # Chain of select_related: student + book + student's profile in one SQL JOIN.

    return render(request, 'circulation/all_records.html', {
        'records':     records,
        'filter_type': filter_type,
        'today':       today,
    })