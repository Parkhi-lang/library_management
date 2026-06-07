from django.db import models


class Book(models.Model):
    """
    Represents one unique title in the library catalog.
    A title can have multiple physical copies — we track that
    with total_copies and available_copies as two separate integers.

    Why not a separate `Copy` model for each physical book?
    For a college library this level of granularity is enough.
    A per-copy model would be needed only if you track individual
    copy conditions, barcodes, or shelf locations.
    """

    title  = models.CharField(max_length=200)
    author = models.CharField(max_length=200)

    isbn = models.CharField(
        max_length=13,
        unique=True,
        # ISBN-13 is internationally unique per title.
        # unique=True puts a UNIQUE constraint in the DB — far more reliable
        # than checking uniqueness in Python, which has race conditions.
    )

    total_copies = models.PositiveIntegerField(default=1)
    # PositiveIntegerField: like IntegerField but rejects 0 and negatives.

    available_copies = models.PositiveIntegerField(default=1)
    # Goes DOWN when borrowed, UP when returned.
    # Should never exceed total_copies — enforced in views.

    category = models.CharField(max_length=100, blank=True, default='')
    # blank=True: optional field. Stores empty string "" when not given.
    # For CharField, blank=True is enough — no need for null=True.

    added_on = models.DateField(auto_now_add=True)
    # auto_now_add=True: set to today once on creation, never changes.

    def is_available(self):
        return self.available_copies > 0

    def __str__(self):
        return f"{self.title} — {self.author}"

    class Meta:
        ordering = ['title']
        # All Book.objects.all() queries come back A→Z by title by default.


class SemesterBook(models.Model):
    """
    Maps a Book to a specific semester + branch + subject.

    Why a separate model instead of fields on Book?
    The SAME book can be prescribed for multiple semesters/branches.
    A separate mapping table handles this cleanly without duplication.
    """

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        # Many SemesterBook rows can point to one Book.
        # CASCADE: deleting the Book also deletes all its assignments.
        related_name='semester_assignments',
        # book.semester_assignments.all() → all assignments for this book.
    )

    semester = models.IntegerField(
        choices=[(i, f'Semester {i}') for i in range(1, 9)],
        # Generates [(1,'Semester 1'), ..., (8,'Semester 8')]
    )

    branch       = models.CharField(max_length=50)   # e.g. "Computer Science"
    subject_name = models.CharField(max_length=100)  # e.g. "Data Structures"

    def __str__(self):
        return f"Sem {self.semester} | {self.branch} | {self.subject_name}"

    class Meta:
        ordering = ['semester', 'subject_name']
        unique_together = ['book', 'semester', 'branch']
        # Same book cannot be prescribed twice for the same semester+branch.