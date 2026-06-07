"""
URL configuration for library_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),

    # include() pulls in each app's urls.py.
    # namespace= must match the app_name inside each urls.py.
    path('accounts/',    include('accounts.urls',    namespace='accounts')),
    path('books/',       include('books.urls',        namespace='books')),
    path('circulation/', include('circulation.urls',  namespace='circulation')),
    path('librarian/',   include('librarian.urls',    namespace='librarian')),

    # Root URL: '' matches 'http://127.0.0.1:8000/'
    # Lambda for a one-liner redirect — no need for a full view function.
    path('', lambda request: redirect('accounts:login'), name='home'),
]