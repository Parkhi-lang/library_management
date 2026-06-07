from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Book, SemesterBook


@login_required
def semester_books_view(request):
    """
    Shows prescribed books for THIS student's semester and branch only.
    Personalises itself by reading the logged-in student's profile.
    """

    if request.user.role == 'librarian':
        from django.shortcuts import redirect
        return redirect('librarian:dashboard')

    profile = request.user.student_profile
    # Access via related_name on OneToOneField — single DB query.

    semester_books = SemesterBook.objects.filter(
        semester=profile.semester,
        branch=profile.branch,
    ).select_related('book')
    # select_related('book') fetches the Book in the same SQL JOIN.
    # Without it, accessing sb.book in the template triggers a separate
    # DB query per row — the N+1 problem.

    return render(request, 'books/semester_books.html', {
        'semester_books': semester_books,
        'profile': profile,
    })


@login_required
def search_books(request):
    """
    Searches semester books by title, author, subject, or category.

    Uses GET not POST so the query appears in the URL (?q=python),
    making results bookmarkable and shareable.
    """

    query = request.GET.get('q', '').strip()
    # .get('q', '') — returns '' if ?q= not in URL (safe default).
    # .strip() — removes accidental spaces from the query.

    results = []

    if query:
        results = SemesterBook.objects.filter(
            Q(book__title__icontains=query)
            # book__title: __ traverses ForeignKey to reach Book.title
            # icontains: case-insensitive LIKE '%query%'

            | Q(book__author__icontains=query)
            # | between Q objects = OR in the SQL WHERE clause

            | Q(subject_name__icontains=query)

            | Q(book__category__icontains=query)

        ).select_related('book').distinct()
        # .distinct() prevents duplicate rows if multiple Q conditions match
        # the same row simultaneously.

    return render(request, 'books/search_results.html', {
        'results': results,
        'query': query,
        # Pass query back so the search box stays pre-filled.
    })