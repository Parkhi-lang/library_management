from django.db import models
from django.conf import settings
from books.models import Book
import datetime


class BorrowRecord(models.Model):
    """
    One row per borrow event. Never deleted — updated on return.
    This gives a permanent borrowing history for every student.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        # Always use settings.AUTH_USER_MODEL, never import CustomUser directly.
        # Avoids tight coupling — works even if user model changes later.
        on_delete=models.CASCADE,
        related_name='borrow_records',
    )

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='borrow_records',
    )

    borrowed_date = models.DateField(auto_now_add=True)
    # Set once on creation, never changes. Records when book was issued.

    due_date = models.DateField()
    # Set explicitly in the view: today + 14 days.
    # Not auto_now_add because due_date is a business rule, not just "today".

    returned_date = models.DateField(null=True, blank=True)
    # null=True: DB column stores NULL until returned.
    # blank=True: form field accepts empty. Both needed for optional date fields.

    is_returned = models.BooleanField(default=False)
    # Faster to query than `returned_date IS NOT NULL`.

    fine_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    # DecimalField for money — never FloatField.
    # FloatField: 0.1 + 0.2 = 0.30000000000000004 (binary float error)
    # DecimalField: 0.10 + 0.20 = 0.30 (exact)

    fine_paid = models.BooleanField(default=False)
    # Separate from fine_amount — a fine can exist but not yet be paid.

    def calculate_fine(self):
        """Called on return. Computes ₹2/day overdue and saves."""
        if self.is_returned and self.returned_date:
            overdue_days = (self.returned_date - self.due_date).days
            # (date - date) = timedelta. .days extracts the integer.
            self.fine_amount = max(0, overdue_days * 2)
            self.save(update_fields=['fine_amount'])
            # update_fields: UPDATE only this column, not the entire row.

    def days_overdue(self):
        """Current days overdue for unreturned books. 0 if not overdue."""
        if not self.is_returned:
            return max(0, (datetime.date.today() - self.due_date).days)
        return 0

    def current_fine_if_returned_today(self):
        """Live fine preview shown to student and librarian."""
        if not self.is_returned:
            overdue = (datetime.date.today() - self.due_date).days
            if overdue > 0:
                return overdue * 2
        return 0

    def __str__(self):
        status = "returned" if self.is_returned else "borrowed"
        return f"{self.student.username} — {self.book.title} ({status})"

    class Meta:
        ordering = ['-borrowed_date']
        # Most recent borrows first. - prefix = descending.