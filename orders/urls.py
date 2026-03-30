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
from .views import CartView, CartItemDetailView, WishlistDetailView, WishlistView, OrderView, OrderDetailView

urlpatterns = [
    path('', OrderView.as_view(), name='orders'),
    path('<int:order_id>', OrderDetailView.as_view(), name='order-detail'),
    path('cart', CartView.as_view(), name='cart'),
    path('cart/<int:item_id>', CartItemDetailView.as_view(), name='cart-item-detail'),
    path('wishlist', WishlistView.as_view(), name='wishlist'),
    path('wishlist/<int:wishlist_id>', WishlistDetailView.as_view(), name='wishlist-detail'),
]
