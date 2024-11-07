"""
URL configuration for Joblet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path
from app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('about/', views.about, name='about'),
    path('profile/<int:user_id>/', views.profile, name='profile'),
    path('profile/<int:user_id>/edit/', views.edit_profile, name='edit_profile'),
    path('services/', views.services, name='services'),
    path('service/<int:service_id>/', views.service_detail, name='service'),
    path('booking/', views.booking, name='booking'),
    path('myorders/', views.myorders, name='myorders'),
    path('myservices/', views.myservices, name='myservices'),
    path('categories/', views.categories, name='categories'),
    path('providers/', views.providers, name='providers'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)