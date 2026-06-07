from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentProfile, LibrarianProfile


class StudentProfileInline(admin.StackedInline):
    """
    Inline lets us edit the StudentProfile on the same admin page as the user.
    Without this, you'd have to navigate to two separate admin pages.
    StackedInline shows fields vertically (good for many fields).
    TabularInline shows fields in a table row (good for few fields).
    """
    model = StudentProfile
    can_delete = False
    # can_delete=False prevents accidentally deleting the profile
    # while editing the user.


class LibrarianProfileInline(admin.StackedInline):
    model = LibrarianProfile
    can_delete = False


@admin.register(CustomUser)
# @admin.register is equivalent to: admin.site.register(CustomUser, CustomUserAdmin)
# It's the modern, decorator-based way to register.
class CustomUserAdmin(UserAdmin):
    """
    We extend UserAdmin (not ModelAdmin) because UserAdmin already knows
    how to handle password fields, hashing display, and permission sections.
    We just add our custom fields to its existing layout.
    """
    inlines = [StudentProfileInline, LibrarianProfileInline]
    # Both inlines are listed. Django shows whichever has an existing row,
    # and shows an empty form for the other.

    # Add `role` to the list view columns
    list_display = ('username', 'email', 'role', 'is_staff')

    # Add `role` to the fieldsets (the edit page sections)
    fieldsets = UserAdmin.fieldsets + (
        ('Library Role', {'fields': ('role',)}),
        # UserAdmin.fieldsets contains all the default sections.
        # We append a new section called "Library Role" with just our field.
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'roll_number', 'semester', 'branch')
    search_fields = ('roll_number', 'user__username')
    # user__username follows the FK to search by the related user's username.


@admin.register(LibrarianProfile)
class LibrarianProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'desk_number')