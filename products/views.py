import csv
import io
import json
from urllib import request
import cloudinary
import requests as http_requests
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Category, Product, ProductImage, SubCategory
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
        product = Product.objects.select_related('category', 'subcategory').all()
        serializer = ProductSerializer(product, many=True)
        total_inventory_value = round(sum([p.price * p.stock for p in product]), 2)
        total_stock_quantity  = sum([p.stock for p in product])
        low_stock_alert       = sum([p.stock < 10 for p in product])
        out_of_stock          = sum([p.stock == 0 for p in product])

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

    parser_classes = [MultiPartParser, FormParser, JSONParser]  # ✅
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

    permission_classes = [AllowAny]
    def get(self, request, product_id):
        try:
            print(request.user)
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

class CategoryView(APIView):

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
    
    permission_classes = [AllowAny]
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
        category_id = request.query_params.get('category', None)

        if category_id:
            subcategories = SubCategory.objects.filter(category__id=category_id)
        else:
            subcategories = SubCategory.objects.all()

        serializer = SubCategorySerializer(subcategories, many=True)
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
            subcategory_name = subcategory.name
            subcategory.delete()
            return Response(
                {'message': f'Subcategory {subcategory_name} deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except SubCategory.DoesNotExist:
            return Response(
                {'message': f'Subcategory with id {subcategory_name} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
class ProductBulkCSVUploadView(APIView):

    permission_classes = [IsAdminUserRole]
    parser_classes     = [MultiPartParser, FormParser]

    # ✅ GET — Download blank CSV template
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products_template.csv"'

        writer = csv.writer(response)

        # ✅ Header row
        writer.writerow([
            'name',
            'description',
            'price',
            'stock',
            'category',
            'subcategory',
            'image_url_1',
            'image_url_2',
            'image_url_3',
            'image_url_4',
            'image_url_5',
        ])

        # ✅ Example rows so admin understands the format
        writer.writerow([
            'Gold Necklace',
            'Beautiful 22kt gold necklace with stone work',
            '1499.00',
            '25',
            'Jewellery',       # exact category name from your DB
            'Necklaces',       # exact subcategory name under that category
            'https://example.com/gold_necklace_1.jpg',
            'https://example.com/gold_necklace_2.jpg',
            '',
            '',
            '',
        ])
        writer.writerow([
            'Silver Bracelet',
            'Pure 925 silver bracelet with floral design',
            '599.00',
            '50',
            'Jewellery',
            'Bracelets',
            'https://example.com/silver_bracelet_1.jpg',
            'https://example.com/silver_bracelet_2.jpg',
            '',
            '',
            '',
        ])

        # ✅ 8 blank rows for admin to fill
        for _ in range(8):
            writer.writerow(['', '', '', '', '', '', '', '', '', '', ''])

        return response

    # ✅ POST — Upload and process CSV
    def post(self, request):
        csv_file = request.FILES.get('file')

        # ── Validations ──────────────────────────────────────────────
        if not csv_file:
            return Response(
                {"message": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not csv_file.name.endswith('.csv'):
            return Response(
                {"message": "File must be a .csv"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if csv_file.size > 10 * 1024 * 1024:  # ✅ 10MB limit (as shown in your UI)
            return Response(
                {"message": "File size must not exceed 10MB"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Parse CSV ─────────────────────────────────────────────────
        try:
            decoded = csv_file.read().decode('utf-8')
        except UnicodeDecodeError:
            return Response(
                {"message": "File encoding not supported. Please save CSV as UTF-8."},
                status=status.HTTP_400_BAD_REQUEST
            )

        reader        = csv.DictReader(io.StringIO(decoded))
        products_data = []
        errors        = []

        # ✅ Validate required columns exist
        required_columns = {'name', 'description', 'price', 'stock', 'category', 'subcategory'}
        if not reader.fieldnames or not required_columns.issubset(set(reader.fieldnames)):
            missing = required_columns - set(reader.fieldnames or [])
            return Response(
                {
                    "message": f"CSV is missing required columns: {', '.join(missing)}",
                    "required_columns": list(required_columns),
                    "optional_columns": ["image_url_1", "image_url_2", "image_url_3", "image_url_4", "image_url_5"],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        for i, row in enumerate(reader, start=2):

            # ✅ Skip completely empty rows
            if not any(row.values()):
                continue

            name             = row.get("name", "").strip()
            description      = row.get("description", "").strip()
            price            = row.get("price", "").strip()
            stock            = row.get("stock", "").strip()
            category_name    = row.get("category", "").strip()
            subcategory_name = row.get("subcategory", "").strip()

            image_urls = []
            for key, value in row.items():
                if key.startswith('image_url_') and value and value.strip().startswith('http'):
                    image_urls.append(value.strip())

            # ── Row-level field validation ────────────────────────────
            row_errors = []

            if not name:
                row_errors.append("'name' is required")

            if not price:
                row_errors.append("'price' is required")
            else:
                try:
                    float(price)
                except ValueError:
                    row_errors.append(f"'price' must be a number, got '{price}'")

            if not stock:
                row_errors.append("'stock' is required")
            else:
                try:
                    int(stock)
                except ValueError:
                    row_errors.append(f"'stock' must be a whole number, got '{stock}'")

            if not category_name:
                row_errors.append("'category' is required")

            if not subcategory_name:
                row_errors.append("'subcategory' is required")

            if row_errors:
                errors.append({"row": i, "name": name or "—", "errors": row_errors})
                continue

            # ── Category / SubCategory lookup ─────────────────────────
            try:
                category = Category.objects.get(name__iexact=category_name)
            except Category.DoesNotExist:
                errors.append({
                    "row": i,
                    "name": name,
                    "errors": [f"Category '{category_name}' not found. Check spelling or create it first."]
                })
                continue

            try:
                subcategory = SubCategory.objects.get(
                    name__iexact=subcategory_name,
                    category=category
                )
            except SubCategory.DoesNotExist:
                errors.append({
                    "row": i,
                    "name": name,
                    "errors": [f"Subcategory '{subcategory_name}' not found under '{category_name}'."]
                })
                continue

            products_data.append({
                "name":        name,
                "description": description,
                "price":       price,
                "stock":       stock,
                "category":    category.id,
                "subcategory": subcategory.id,
                "_image_urls": image_urls,
            })

        # ── Return row errors before saving anything ──────────────────
        if errors:
            return Response(
                {
                    "message":      f"{len(errors)} row(s) have errors. No products were uploaded. Fix and re-upload.",
                    "total_errors": len(errors),
                    "errors":       errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not products_data:
            return Response(
                {"message": "CSV has no valid product rows to import."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        saved_products    = []
        image_upload_logs = []

        # ── Save all products ─────────────────────────────────────────
        for product_row in products_data:

            # Pop image URLs before passing to serializer
            image_urls = product_row.pop('_image_urls', [])

            # ✅ Save the product
            serializer = ProductSerializer(data=product_row)
            if not serializer.is_valid():
                errors.append({
                    "name":   product_row.get("name"),
                    "errors": serializer.errors
                })
                continue

            product = serializer.save()
            saved_products.append(serializer.data)

            # ✅ Upload each image URL to Cloudinary and save ProductImage
            uploaded_images = []
            failed_images   = []

            for img_url in image_urls:
                try:
                    # Fetch the image from URL
                    img_response = http_requests.get(img_url, timeout=10)

                    if img_response.status_code != 200:
                        failed_images.append({
                            "url":   img_url,
                            "error": f"Could not fetch image. HTTP {img_response.status_code}"
                        })
                        continue

                    # Upload to Cloudinary
                    upload_result = cloudinary.uploader.upload(
                        img_response.content,
                        folder    = "products/",
                        overwrite = False,
                    )

                    # Save to ProductImage
                    ProductImage.objects.create(
                        product   = product,
                        image_url = upload_result['public_id']
                    )

                    uploaded_images.append(upload_result['secure_url'])

                except http_requests.exceptions.Timeout:
                    failed_images.append({"url": img_url, "error": "Request timed out"})
                except http_requests.exceptions.RequestException as e:
                    failed_images.append({"url": img_url, "error": f"Network error: {str(e)}"})
                except Exception as e:
                    failed_images.append({"url": img_url, "error": f"Cloudinary error: {str(e)}"})

            image_upload_logs.append({
                "product":          product.name,
                "product_id":       product.id,
                "images_uploaded":  len(uploaded_images),
                "images_failed":    len(failed_images),
                "uploaded_urls":    uploaded_images,
                "failed":           failed_images,
            })

        # ── Build final response ──────────────────────────────────────
        total_images_uploaded = sum(l['images_uploaded'] for l in image_upload_logs)
        total_images_failed   = sum(l['images_failed']   for l in image_upload_logs)

        return Response(
            {
                "message": f"✅ {len(saved_products)} product(s) uploaded with {total_images_uploaded} image(s).",
                "summary": {
                    "products_uploaded":     len(saved_products),
                    "products_failed":       len(errors),
                    "total_images_uploaded": total_images_uploaded,
                    "total_images_failed":   total_images_failed,
                },
                "products":     saved_products,
                "image_logs":   image_upload_logs,
                "errors":       errors,
            },
            status=status.HTTP_201_CREATED
        )


# ── Keep ProductImageUploadView for single product image upload ───────────────
class ProductImageUploadView(APIView):
    """Used to add more images to an existing product after creation."""

    permission_classes = [IsAdminUserRole]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        product_id   = request.data.get('product_id')
        product_name = request.data.get('product_name')
        images       = request.FILES.getlist('images')

        if not images:
            return Response(
                {"message": "No images provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if product_id:
                product = Product.objects.get(id=product_id)
            elif product_name:
                product = Product.objects.get(name__iexact=product_name)
            else:
                return Response(
                    {"message": "Provide either product_id or product_name"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Product.DoesNotExist:
            return Response({"message": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        except Product.MultipleObjectsReturned:
            return Response(
                {"message": f"Multiple products found with name '{product_name}'. Use product_id instead."},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded, failed = [], []
        for image_file in images:
            try:
                upload_result = cloudinary.uploader.upload(image_file, folder="products/")
                ProductImage.objects.create(product=product, image_url=upload_result['public_id'])
                uploaded.append(upload_result['secure_url'])
            except Exception as e:
                failed.append({"file": image_file.name, "error": str(e)})

        return Response(
            {
                "message":  f"{len(uploaded)} image(s) uploaded for '{product.name}'",
                "uploaded": uploaded,
                "failed":   failed
            },
            status=status.HTTP_201_CREATED
        )