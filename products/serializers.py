from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Product, Category, SubCategory, ProductImage
import cloudinary.uploader


class CategorySerializer(ModelSerializer):
    category_image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = Category
        fields = "__all__"

    def get_category_image_url(self, obj):
        try:
            return obj.category_image.url if obj.category_image else None
        except Exception:
            return None


class SubCategorySerializer(ModelSerializer):
    class Meta:
        model  = SubCategory
        fields = "__all__"


class ProductImageSerializer(ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = ProductImage
        fields = ["id", "image_url"]

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None


class ProductSerializer(serializers.ModelSerializer):
    # ✅ Accepts multiple image files on write (multipart/form-data)
    product_images = serializers.ListField(
        child=serializers.ImageField(),   # was URLField — now accepts actual files
        write_only=True,
        required=False
    )
    # ✅ Returns image objects with URLs on read
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model  = Product
        fields = "__all__"

    def create(self, validated_data):
        images_data = validated_data.pop('product_images', [])
        product     = Product.objects.create(**validated_data)

        for image_file in images_data:
            # ✅ Upload each file to Cloudinary, get back a secure URL
            upload_result = cloudinary.uploader.upload(
                image_file,
                folder="products/"          # organizes uploads in Cloudinary dashboard
            )
            ProductImage.objects.create(
                product=product,
                image=upload_result['public_id']  # store Cloudinary public_id
            )

        return product

    def update(self, instance, validated_data):
        images_data = validated_data.pop('product_images', [])

        # Update the product fields normally
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # ✅ Append new images if provided (does NOT delete existing ones)
        for image_file in images_data:
            upload_result = cloudinary.uploader.upload(
                image_file,
                folder="products/"
            )
            ProductImage.objects.create(
                product=instance,
                image=upload_result['public_id']
            )

        return instance