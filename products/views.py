import json
from urllib import request
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Category, Product, SubCategory
from .serializers import CategorySerializer, ProductSerializer, SubCategorySerializer
from users.permissions import IsAdminUserRole



class ProductView(APIView):

    permission_classes = [IsAdminUserRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        data = request.data

        if isinstance(data, list):
            serializer = ProductSerializer(data=data, many=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Bulk products created successfully", "data": serializer.data},
                    status=status.HTTP_201_CREATED
                )
            return Response(
                {"message": "Bulk creation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ProductSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Product created successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"message": "Product creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    permission_classes = [AllowAny]
    def get(self, request):
        product = Product.objects.all()
        serializer = ProductSerializer(product, many=True)
        total_inventory_value = round(sum([p.price * p.stock for p in product]), 2)
        total_stock_quantity  = sum([p.stock for p in product])
        low_stock_alert       = any(p.stock < 10 for p in product)
        out_of_stock          = any(p.stock == 0 for p in product)

        return Response(
            {
                "message": "Products retrieved successfully",
                "data": serializer.data,
                "total_inventory_value": total_inventory_value,
                "total_stock_quantity": total_stock_quantity,
                "low_stock_alert": low_stock_alert,
                "out_of_stock": out_of_stock,
            },
            status=status.HTTP_200_OK
        )


class ProductDetailView(APIView):

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # ✅

    def get(self, request, product_id):
        try:
            product    = Product.objects.get(id=product_id)
            serializer = ProductSerializer(product)
            return Response(
                {'message': f'Details of product {product_id}', 'data': serializer.data},
                status=status.HTTP_200_OK
            )
        except Product.DoesNotExist:
            return Response(
                {'message': f'Product with id {product_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    permission_classes = [IsAdminUserRole]
    def put(self, request, product_id):
        try:
            product    = Product.objects.get(id=product_id)
            serializer = ProductSerializer(product, data=request.data, partial=True)  # ✅ partial=True
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {'message': f'Product {product_id} updated successfully', 'data': serializer.data},
                    status=status.HTTP_200_OK
                )
            return Response(
                {'message': 'Update failed', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Product.DoesNotExist:
            return Response(
                {'message': f'Product with id {product_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    permission_classes = [IsAdminUserRole]
    def delete(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            product.delete()
            return Response(
                {'message': f'Product {product_id} deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Product.DoesNotExist:
            return Response(
                {'message': f'Product with id {product_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class CategoryView(APIView):

    permission_classes = [IsAdminUserRole, AllowAny]
    def get(self, request):

        categories = Category.objects.all()
        sub_categoty_count = SubCategory.objects.count()
        inactive_categories = categories.filter(status='inactive').count()
        active_categories = categories.filter(status='active').count()
        total_categories = categories.count()
        sub_items_count = sub_categoty_count
        serializer = CategorySerializer(categories, many=True)
        return Response(
            {
                "message": "Categories retrieved successfully",
                "data": serializer.data,
                "total_categories": total_categories,
                "subcategory_count": sub_items_count,
                "active": active_categories,
                "inactive": inactive_categories,
            },
            status=status.HTTP_200_OK
        )

    parser_classes = [MultiPartParser, FormParser, JSONParser]  # ✅
    permission_classes = [IsAdminUserRole]
    def post(self, request):
        data = request.data
        serializer = CategorySerializer(data={
            'name':           data.get('name'),
            'description':    data.get('description', None),
            'category_image': data.get('category_image', None) or request.FILES.get('category_image')  # ✅
        })

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'Category added successfully',
                    'data': serializer.data
                 },
                status=status.HTTP_201_CREATED
            )
        return Response(
            {'message': 'Category creation failed', 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class CategoryDetailView(APIView):
    
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # ✅
    permission_classes = [AllowAny]
    def get(self, request, category_id):
        try:
            category   = Category.objects.get(id=category_id)
            serializer = CategorySerializer(category)
            return Response(
                {'message': f'Details of category {category_id}', 'data': serializer.data},
                status=status.HTTP_200_OK
            )
        except Category.DoesNotExist:
            return Response(
                {'message': f'Category with id {category_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    permission_classes = [IsAdminUserRole]
    def put(self, request, category_id):
        try:
            category   = Category.objects.get(id=category_id)
            serializer = CategorySerializer(category, data=request.data, partial=True)  # ✅ partial=True
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {'message': f'Category {category_id} updated successfully', 'data': serializer.data},
                    status=status.HTTP_200_OK
                )
            return Response(
                {'message': 'Update failed', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Category.DoesNotExist:
            return Response(
                {'message': f'Category with id {category_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, category_id):
        try:
            category = Category.objects.get(id=category_id)
            category_name = category.name
            category.delete()
            return Response(
                {'message': f'Category {category_name} deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Category.DoesNotExist:
            return Response(
                {'message': f'Category with id {category_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SubCategoryView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # ✅

    # def get_permissions(self):
    #     if self.request.method == 'GET':
    #         print("Self ------->", self.request)
    #         return [AllowAny()]
    #     return [IsAdminUserRole()]

    permission_classes = [IsAdminUserRole]
    def post(self, request):
        data = request.data
        serializer = SubCategorySerializer(data={
            'name':        data.get('subcategory_name'),
            'description': data.get('description', None),
            'category':    data.get('category', None),
            'image':       data.get('image', None) or request.FILES.get('image')  # ✅
        })

        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Subcategory added successfully', 'data': serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {'message': 'Subcategory creation failed', 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    permission_classes = [AllowAny]
    def get(self, request):
        subcategories = SubCategory.objects.all()
        serializer    = SubCategorySerializer(subcategories, many=True)
        return Response(
            {'message': 'List of subcategories', 'data': serializer.data},
            status=status.HTTP_200_OK
        )


class SubCategoryDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # ✅

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUserRole()]

    def get(self, request, subcategory_id):
        try:
            subcategory = SubCategory.objects.get(id=subcategory_id)
            serializer  = SubCategorySerializer(subcategory)
            return Response(
                {'message': f'Details of subcategory {subcategory_id}', 'data': serializer.data},
                status=status.HTTP_200_OK
            )
        except SubCategory.DoesNotExist:
            return Response(
                {'message': f'Subcategory with id {subcategory_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, subcategory_id):
        try:
            subcategory = SubCategory.objects.get(id=subcategory_id)
            serializer  = SubCategorySerializer(subcategory, data=request.data, partial=True)  # ✅ partial=True
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {'message': f'Subcategory {subcategory_id} updated successfully', 'data': serializer.data},
                    status=status.HTTP_200_OK
                )
            return Response(
                {'message': 'Update failed', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except SubCategory.DoesNotExist:
            return Response(
                {'message': f'Subcategory with id {subcategory_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, subcategory_id):
        try:
            subcategory = SubCategory.objects.get(id=subcategory_id)
            subcategory.delete()
            return Response(
                {'message': f'Subcategory {subcategory_id} deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except SubCategory.DoesNotExist:
            return Response(
                {'message': f'Subcategory with id {subcategory_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )