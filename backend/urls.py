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

from appointments.views import AdminAppointmentListView
from policies.views import AdminPolicyAuditView, AdminPolicyDetailView, AdminPolicyView
from orders.views import AdminCouponDetailView, AdminCouponToggleStatusView, AdminCouponToggleStatusView, \
    AdminCouponView, AdminDashboardView, AdminOrderListView, AdminOrderUpdateStatusView, AdminSalesAnalyticsView, \
    AdminTopProductsView, AdminUsersView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/products/', include('products.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/policies/', include('policies.urls')),
    # ====== Admin Panel URLs ======
    path('api/admin-panel/dashboard', AdminDashboardView.as_view()),
    path('api/admin-panel/orders', AdminOrderListView.as_view()),
    path('api/admin-panel/orders/<int:order_id>/status', AdminOrderUpdateStatusView.as_view()),
    path('api/admin-panel/sales', AdminSalesAnalyticsView.as_view()),
    path('api/admin-panel/users', AdminUsersView.as_view()),
    path('api/admin-panel/top-products', AdminTopProductsView.as_view()),
    path('api/admin-panel/appointments', AdminAppointmentListView.as_view()),
    path('api/admin-panel/coupons/', AdminCouponView.as_view(), name='admin-coupons'),
    path('api/admin-panel/coupons/<int:coupon_id>/', AdminCouponDetailView.as_view(), name='admin-coupon-detail'),
    path('api/admin-panel/coupons/<int:coupon_id>/toggle-status/', AdminCouponToggleStatusView.as_view(), name='admin-coupon-toggle'),
    path('api/admin-panel/policies/', AdminPolicyView.as_view(), name='admin-policies'),
    path('api/admin-panel/policies/<int:policy_id>/', AdminPolicyDetailView.as_view(), name='admin-policy-detail'),
    path('api/admin-panel/policies/audit/', AdminPolicyAuditView.as_view(), name='admin-policy-audit'),

]
