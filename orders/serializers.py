from rest_framework import serializers
from .models import Cart, CartItem, Wishlist, Order, OrderItem
from products.models import Product

class CartItemSerializer(serializers.ModelSerializer):

    product_details = serializers.SerializerMethodField()
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_details', 'quantity', 'price', 'total_price']
        read_only_fields = ['price']   # ✅ FIX

    def get_product_details(self, obj):
        if not obj.product:
            return None
        image = obj.product.images.first()
        return {
            "id": obj.product.id,
            "name": obj.product.name,
            "price": obj.product.price,
            "image": image.image_url.url if image and image.image_url else None
        }
    
class CartSerializer(serializers.ModelSerializer):

    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'created_at']

class WishlistSerializer(serializers.ModelSerializer):

    product_details = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'product', 'product_details', 'created_at']

    def get_product_details(self, obj):
        image = obj.product.images.first()
        return {
            "id": obj.product.id,
            "name": obj.product.name,
            "price": obj.product.price,
            "image": image.image_url.url if image and image.image_url else None
        }
    
class OrderItemSerializer(serializers.ModelSerializer):

    product_details = serializers.SerializerMethodField()
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_details', 'quantity', 'price', 'total_price']

    def get_product_details(self, obj):
        print("Getting product details for OrderItem:", obj.product)
        image = obj.product.images.first()
        return {
            "id": obj.product.id if obj.product else None,
            "name": obj.product.name if obj.product else None,
            "price": obj.price,
            "image": image.image_url.url if image and image.image_url else None
        }
    
class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'items',
            'total_amount',
            'status',
            'address',
            'city',
            'pincode',
            'created_at'
        ]
        read_only_fields = ['user', 'status', 'total_amount']

    def validate(self, data):
        user = self.context['request'].user

        # check cart exists
        if not hasattr(user, 'cart'):
            raise serializers.ValidationError("Cart not found")

        # check cart items
        if not user.cart.items.exists():
            raise serializers.ValidationError("Cart is empty")

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        cart = user.cart

        order = Order.objects.create(
            user=user,
            address=validated_data.get('address'),
            city=validated_data.get('city'),
            pincode=validated_data.get('pincode')
        )

        total = 0

        for item in cart.items.all():

            # ✅ Check if enough stock is available before placing order
            if item.product.stock < item.quantity:
                order.delete()  # rollback the order
                raise serializers.ValidationError(
                    f"Insufficient stock for '{item.product.name}'. "
                    f"Available: {item.product.stock}, Requested: {item.quantity}"
                )

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.price
            )

            # ✅ Deduct stock after order item is created
            item.product.stock -= item.quantity
            item.product.save()

            total += item.total_price

        order.total_amount = total
        order.save()

        cart.items.all().delete()  # clear cart after order

        return order