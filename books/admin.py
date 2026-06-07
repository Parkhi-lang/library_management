from django.contrib import admin
from .models import Book, SemesterBook


class SemesterBookInline(admin.TabularInline):
    """
    Shows semester assignments directly on the Book admin page.
    TabularInline = compact table row layout (good for few fields).
    StackedInline = expanded vertical layout (good for many fields).
    """
    model = SemesterBook
    extra = 1
    # extra=1: always show 1 blank row so librarian can add immediately.


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    inlines       = [SemesterBookInline]
    list_display  = ('title', 'author', 'isbn', 'total_copies', 'available_copies', 'added_on')
    list_filter   = ('category', 'added_on')
    search_fields = ('title', 'author', 'isbn')
    readonly_fields = ('added_on',)

    fieldsets = (
        ('Book Information', {'fields': ('title', 'author', 'isbn', 'category')}),
        ('Inventory',        {'fields': ('total_copies', 'available_copies')}),
        ('Metadata',         {'fields': ('added_on',), 'classes': ('collapse',)}),
    )


@admin.register(SemesterBook)
class SemesterBookAdmin(admin.ModelAdmin):
    list_display  = ('subject_name', 'semester', 'branch', 'book')
    list_filter   = ('semester', 'branch')
    search_fields = ('subject_name', 'book__title', 'branch')
    # book__title: follow ForeignKey with __ to search related model's field.