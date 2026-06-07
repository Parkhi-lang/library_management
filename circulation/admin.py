from django.contrib import admin
from django.utils.html import format_html
from .models import BorrowRecord
import datetime


@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):

    list_display  = ('student', 'book', 'borrowed_date', 'due_date',
                     'is_returned', 'fine_amount', 'fine_paid', 'status_badge')
    list_filter   = ('is_returned', 'fine_paid', 'borrowed_date')
    search_fields = ('student__username', 'student__student_profile__roll_number', 'book__title')
    readonly_fields = ('borrowed_date', 'fine_amount')
    list_editable   = ('is_returned', 'fine_paid')

    def status_badge(self, obj):
        """Colored HTML badge — green/orange/red based on state."""
        today = datetime.date.today()
        if obj.is_returned:
            color, label = '#3dd68c', 'Returned'
        elif obj.due_date < today:
            color, label = '#ff4d6a', f'Overdue {(today - obj.due_date).days}d'
        else:
            color, label = '#ffb237', f'Due in {(obj.due_date - today).days}d'

        return format_html(
            '<span style="background:{}22;color:{};padding:2px 8px;'
            'border-radius:10px;font-size:12px;font-weight:600">{}</span>',
            color, color, label
            # {}22 appends "22" to hex color → ~13% opacity background.
        )
    status_badge.short_description = 'Status'

    fieldsets = (
        ('Borrow Details', {'fields': ('student', 'book', 'borrowed_date', 'due_date')}),
        ('Return Info',    {'fields': ('is_returned', 'returned_date')}),
        ('Fine',           {'fields': ('fine_amount', 'fine_paid')}),
    )