# policies/urls.py
from django.urls import path
from .views import (
    AdminPolicyView, AdminPolicyDetailView,
    PublicPolicyView, AdminPolicyAuditView
)

urlpatterns = [
    # Public (for your React storefront)
    path('policies/<str:policy_type>/',            PublicPolicyView.as_view(),      name='public-policy'),
]