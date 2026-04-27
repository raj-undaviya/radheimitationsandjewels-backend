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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from .views import ProductBulkCSVUploadView, ProductView, ProductDetailView, CategoryView, \
      SubCategoryDetailView, SubCategoryView, CategoryDetailView, ProductImageUploadView

urlpatterns = [
    path('', ProductView.as_view(), name='product'),
    path('<int:product_id>', ProductDetailView.as_view(), name='product-detail'),
    path('category', CategoryView.as_view(), name='category'),
    path('category/<int:category_id>', CategoryDetailView.as_view(), name='category-detail'),
    path('subcategory', SubCategoryView.as_view(), name='subcategory'),
    path('subcategory/<int:subcategory_id>', SubCategoryDetailView.as_view(), name='subcategory-detail'),
    path('bulk-upload/',   ProductBulkCSVUploadView.as_view(), name='product-bulk-upload'),
    path('upload-images/', ProductImageUploadView.as_view(),   name='product-image-upload'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)