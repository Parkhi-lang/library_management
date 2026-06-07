from django.urls import path
from . import views

app_name = 'librarian'

urlpatterns = [
    path('dashboard/',      views.dashboard,      name='dashboard'),
    # /librarian/dashboard/ → stats + activity + overdue panel

    path('student-lookup/', views.student_lookup, name='student_lookup'),
    # /librarian/student-lookup/?roll=CS2022001 → student record

    path('inventory/',      views.inventory_view, name='inventory'),
    # /librarian/inventory/ → add books, update copy counts

    path('overdue/',        views.overdue_alerts, name='overdue_alerts'),
    # /librarian/overdue/ → full overdue list with fine previews + defaulters
]