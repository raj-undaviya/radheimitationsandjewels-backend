"""
URL configuration for backend project.

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
from django.urls import path
from .views import AppointmentView, \
    AppointmentDetailView, UserAppointmentListView, UserAppointmentTimeSlotsView, \
    AdminAppointmentExportCSVView

urlpatterns = [
    path('', AppointmentView.as_view(), name='appointments'),
    path('time-slots', UserAppointmentTimeSlotsView.as_view(), name='appointment-time-slots'),
    path('<int:appointment_id>', AppointmentDetailView.as_view(), name='appointment-detail'),
    path('my', UserAppointmentListView.as_view(), name='my-appointments'),
    path('export-csv', AdminAppointmentExportCSVView.as_view(), name='admin-appointments-csv'),
]
