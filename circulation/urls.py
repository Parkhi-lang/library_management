from django.urls import path
from . import views

app_name = 'circulation'

urlpatterns = [
    path('my-books/',               views.my_borrowed_books, name='my_borrowed_books'),
    path('issue/',                  views.issue_book,        name='issue_book'),
    path('return/<int:record_id>/', views.return_book,       name='return_book'),
    # <int:record_id>: captures integer from URL, passes as `record_id` param.
    # /return/abc/ returns 404 automatically — type is enforced.
    path('records/',                views.all_borrow_records, name='all_records'),
]