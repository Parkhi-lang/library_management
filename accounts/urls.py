from django.urls import path
from . import views

# app_name sets the namespace for this app's URLs.
# This means we reference them as 'accounts:login', 'accounts:logout', etc.
# Why namespaces? If two apps both had a view named 'login', Django would
# not know which one {% url 'login' %} refers to. Namespaces fix that.
app_name = 'accounts'

urlpatterns = [
    path('login/',    views.login_view,          name='login'),
    path('logout/',   views.logout_view,          name='logout'),
    path('register/', views.register_student,     name='register'),
    path('redirect/', views.role_redirect,        name='role_redirect'),
    path('profile/',  views.student_profile_view, name='student_profile'),
]