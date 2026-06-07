from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from functools import wraps
import datetime

from accounts.models import CustomUser, StudentProfile
from books.models import Book, SemesterBook
from circulation.models import BorrowRecord


def librarian_required(view_func):
    """
    Custom decorator: login check + librarian role check.
    Each app defines it locally — avoids cross-app import dependencies.
    In a larger project, put shared decorators in a project-level utils.py.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_librarian():
            messages.error(request, "Access denied. Librarians only.")
            return redirect('accounts:student_profile')
        return view_func(request, *args, **kwargs)
    return wrapper


@librarian_required
def dashboard(request):
    """
    Librarian home page — five stat cards, recent activity table,
    top-5 overdue panel, quick action buttons.
    All read-only. Write operations happen in other views.
    """
    today = datetime.date.today()

    total_students = CustomUser.objects.filter(role='student').count()
    # .count() = SELECT COUNT(*) — doesn't load objects into memory.
    # Always use .count() instead of len(queryset) for counting.

    total_books            = Book.objects.count()
    currently_borrowed     = BorrowRecord.objects.filter(is_returned=False).count()
    overdue_count          = BorrowRecord.objects.filter(
                                is_returned=False, due_date__lt=today
                             ).count()
    # due_date__lt = due_date < today (lt = less than)

    total_fine_outstanding = BorrowRecord.objects.filter(
        fine_paid=False, fine_amount__gt=0
    ).aggregate(total=Sum('fine_amount'))['total'] or 0

    recent_activity = BorrowRecord.objects.all()\
        .select_related('student', 'book', 'student__student_profile')\
        .order_by('-id')[:8]
    # order_by('-id'): insertion order (newest first).
    # [:8]: SQL LIMIT 8 — only fetches 8 rows from DB.

    overdue_records = BorrowRecord.objects.filter(
        is_returned=False, due_date__lt=today
    ).select_related('student', 'book', 'student__student_profile')\
     .order_by('due_date')[:5]
    # order_by('due_date') ascending = most overdue (oldest date) first.

    return render(request, 'librarian/dashboard.html', {
        'total_students':         total_students,
        'total_books':            total_books,
        'currently_borrowed':     currently_borrowed,
        'overdue_count':          overdue_count,
        'total_fine_outstanding': total_fine_outstanding,
        'recent_activity':        recent_activity,
        'overdue_records':        overdue_records,
        'today':                  today,
    })


@librarian_required
def student_lookup(request):
    """
    Librarian searches by roll number → sees student's full record.
    Uses GET so the roll number appears in URL (?roll=CS2022001),
    making student pages bookmarkable.
    """
    student = profile = None
    active_borrows = past_borrows = []
    total_fine  = 0
    roll_number = request.GET.get('roll', '').strip()

    if roll_number:
        try:
            profile = StudentProfile.objects.select_related('user').get(
                roll_number=roll_number
            )
            # select_related('user'): fetches CustomUser in same query — no second hit.
            student = profile.user

            active_borrows = BorrowRecord.objects.filter(
                student=student, is_returned=False
            ).select_related('book').order_by('due_date')
            # order_by('due_date'): most urgent (soonest due) first.

            past_borrows = BorrowRecord.objects.filter(
                student=student, is_returned=True
            ).select_related('book').order_by('-returned_date')

            total_fine = BorrowRecord.objects.filter(
                student=student, fine_paid=False, fine_amount__gt=0
            ).aggregate(total=Sum('fine_amount'))['total'] or 0

        except StudentProfile.DoesNotExist:
            messages.error(request, f"No student found with roll number: {roll_number}")

    return render(request, 'librarian/student_lookup.html', {
        'student': student, 'profile': profile,
        'active_borrows': active_borrows, 'past_borrows': past_borrows,
        'total_fine': total_fine, 'roll_number': roll_number,
        'today': datetime.date.today(),
    })


@librarian_required
def inventory_view(request):
    """
    Book catalog manager. One view handles two POST actions:
      action='add'           → create a new Book
      action='update_copies' → update copy count of an existing Book
    Identified by a hidden form field called `action`.
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            title    = request.POST.get('title', '').strip()
            author   = request.POST.get('author', '').strip()
            isbn     = request.POST.get('isbn', '').strip()
            copies   = int(request.POST.get('copies', 1))
            category = request.POST.get('category', '').strip()

            if not all([title, author, isbn]):
                messages.error(request, "Title, author, and ISBN are required.")
                return redirect('librarian:inventory')

            if Book.objects.filter(isbn=isbn).exists():
                messages.error(request, f"A book with ISBN {isbn} already exists.")
                return redirect('librarian:inventory')

            Book.objects.create(
                title=title, author=author, isbn=isbn, category=category,
                total_copies=copies, available_copies=copies,
                # New book: available = total (none borrowed yet)
            )
            messages.success(request, f'"{title}" added to inventory.')

        elif action == 'update_copies':
            book_id = request.POST.get('book_id')
            total   = int(request.POST.get('total_copies', 1))
            book    = get_object_or_404(Book, id=book_id)

            borrowed_count = BorrowRecord.objects.filter(
                book=book, is_returned=False
            ).count()

            available = max(0, total - borrowed_count)
            # max(0, ...): available can never be negative even if
            # librarian sets total lower than currently borrowed count.

            book.total_copies     = total
            book.available_copies = available
            book.save(update_fields=['total_copies', 'available_copies'])
            messages.success(request, f'"{book.title}" updated: {total} total, {available} available.')

        return redirect('librarian:inventory')

    # GET: annotate each book with historical borrow count
    books = Book.objects.annotate(
        times_borrowed=Count(
            'borrow_records',
            filter=Q(borrow_records__is_returned=True)
            # Count only returned borrows = historical usage stat
        )
    ).order_by('title')
    # annotate() adds a .times_borrowed attribute to every book object.
    # It runs in a single SQL query with GROUP BY — not a Python loop.

    return render(request, 'librarian/inventory.html', {'books': books})


@librarian_required
def overdue_alerts(request):
    """
    Full overdue list sorted by most overdue first.
    Also computes top defaulters (students with multiple overdue books).
    """
    today = datetime.date.today()

    overdue_records = BorrowRecord.objects.filter(
        is_returned=False, due_date__lt=today
    ).select_related('student', 'book', 'student__student_profile')\
     .order_by('due_date')

    # Python-side annotation — days and fine preview per record
    records_annotated = []
    for record in overdue_records:
        days = (today - record.due_date).days
        records_annotated.append({
            'record':       record,
            'days_overdue': days,
            'fine_preview': days * 2,   # ₹2/day — display only, not saved
        })

    total_overdue_fine_preview = sum(r['fine_preview'] for r in records_annotated)

    # Group by student → find students with multiple overdue books
    students_with_overdue = {}
    for item in records_annotated:
        sid = item['record'].student.id
        if sid not in students_with_overdue:
            students_with_overdue[sid] = {
                'student': item['record'].student,
                'count':   0,
            }
        students_with_overdue[sid]['count'] += 1

    top_defaulters = sorted(
        students_with_overdue.values(),
        key=lambda x: x['count'],
        reverse=True
    )[:5]

    return render(request, 'librarian/overdue_alerts.html', {
        'records_annotated':          records_annotated,
        'total_overdue_fine_preview': total_overdue_fine_preview,
        'top_defaulters':             top_defaulters,
        'today':                      today,
    })