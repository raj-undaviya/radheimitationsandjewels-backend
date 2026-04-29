# policies/urls.py
from django.urls import path
from .views import (
    AdminPolicyView, AdminPolicyDetailView,
    PublicPolicyView, AdminPolicyAuditView,
    UserPolicyView, UserPolicyDetailView
)

urlpatterns = [
    # Public (for your React storefront)
    path('<str:policy_type>/',            PublicPolicyView.as_view(),      name='public-policy'),
    path('user/<str:policy_type>/',       UserPolicyDetailView.as_view(),        name='user-policy-detail'),
    path('user/',                         UserPolicyView.as_view(),              name='user-policies'),
]