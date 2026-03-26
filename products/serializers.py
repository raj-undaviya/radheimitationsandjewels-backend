from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Product, Category, SubCategory, ProductImage


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"

class SubCategorySerializer(ModelSerializer):
    class Meta:
        model = SubCategory
        fields = "__all__"

class ProductImageSerializer(ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image_url"]

class ProductSerializer(serializers.ModelSerializer):
    product_images = serializers.ListField(
        child=serializers.URLField(),
        write_only=True,
        required=False
    )
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"

    def create(self, validated_data):

        images_data = validated_data.pop('product_images', [])
        product = Product.objects.create(**validated_data)

        for image_url in images_data:
            ProductImage.objects.create(
                product=product,
                image_url=image_url
            )

        return product