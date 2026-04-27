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
    parent_category_name = serializers.CharField(source='category.name', read_only=True)
    items_count          = serializers.SerializerMethodField(read_only=True)
    image_url            = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = SubCategory
        fields = "__all__"

    def get_items_count(self, obj):
        return obj.products.count()  # adjust if your related_name is different

    def get_image_url(self, obj):
        try:
            return obj.image.url if obj.image else None
        except Exception:
            return None


class ProductImageSerializer(ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = ProductImage
        fields = ["id", "image_url"]

    def get_image_url(self, obj):
        return obj.image_url.url if obj.image_url else None

class ProductSerializer(serializers.ModelSerializer):
    product_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    images             = ProductImageSerializer(many=True, read_only=True)
    category_name      = serializers.CharField(source='category.name',    read_only=True)  # ✅
    subcategory_name   = serializers.CharField(source='subcategory.name', read_only=True)  # ✅

    class Meta:
        model  = Product
        fields = "__all__"

    def create(self, validated_data):
        images_data = validated_data.pop('product_images', [])
        product     = Product.objects.create(**validated_data)

        for image_file in images_data:
            upload_result = cloudinary.uploader.upload(
                image_file,
                folder="products/"
            )
            ProductImage.objects.create(
                product=product,
                image_url=upload_result['public_id']
            )

        return product

    def update(self, instance, validated_data):
        images_data = validated_data.pop('product_images', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        for image_file in images_data:
            upload_result = cloudinary.uploader.upload(
                image_file,
                folder="products/"
            )
            ProductImage.objects.create(
                product=instance,
                image_url=upload_result['public_id']
            )

        return instance