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
from django.contrib import admin
from django.urls import include, path

from .views import AddressDetailView, AddressListCreateView, AuthenticateView, ForgetPasswordView, \
      UserProfileView, SetDefaultAddressView, VerifyOTPView, CustomersView, CustomersDetailView, LogoutView

urlpatterns = [
    path('auth/', AuthenticateView.as_view(), name='authenticate'),
    path('forget-password/', ForgetPasswordView.as_view(), name='forget-password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('customers/', CustomersView.as_view(), name='customers'),
    path('customers/<int:customer_id>/', CustomersDetailView.as_view(), name='customer-detail'),

    path('profile/',                             UserProfileView.as_view()),
    path('addresses/',                           AddressListCreateView.as_view()),
    path('addresses/<int:pk>/',                  AddressDetailView.as_view()),
    path('addresses/<int:pk>/set-default/',      SetDefaultAddressView.as_view()),
]
