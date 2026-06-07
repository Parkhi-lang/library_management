from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    path('my-books/', views.semester_books_view, name='semester_books'),
    # /books/my-books/ → student's prescribed books

    path('search/', views.search_books, name='search'),
    # /books/search/?q=python → search results
]