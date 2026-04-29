from rest_framework import serializers
from .models import Cart, CartItem, Coupon, Wishlist, Order, OrderItem
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
        image = obj.product.images.first()
        return {
            "id": obj.product.id if obj.product else None,
            "name": obj.product.name if obj.product else None,
            "price": obj.price,
            "image": image.image_url.url if image and image.image_url else None
        }
    
# serializers.py
class OrderSerializer(serializers.ModelSerializer):

    items        = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.ReadOnlyField()
    coupon_code = serializers.CharField(write_only=True, required=False)  # ✅

    class Meta:
        model  = Order
        fields = [
            'id',
            'user',
            'items',
            'total_amount',
            'status',
            'payment_method',       # ✅ new
            'payment_status',       # ✅ new
            'razorpay_order_id',    # ✅ new
            'razorpay_payment_id',  # ✅ new
            'address',
            'city',
            'pincode',
            'created_at',
            'coupon_code',      # ✅ write only — for input
            'discount_amount',  # ✅ read only — saved on order
        ]
        read_only_fields = ['user', 'status', 'total_amount', 'payment_status', 'razorpay_order_id']

    def validate(self, data):
        user = self.context['request'].user

        if not hasattr(user, 'cart'):
            raise serializers.ValidationError("Cart not found")

        if not user.cart.items.exists():
            raise serializers.ValidationError("Cart is empty")

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        cart = user.cart
        coupon_code = validated_data.pop('coupon_code', None)

        order = Order.objects.create(
            user           = user,
            address        = validated_data.get('address'),
            city           = validated_data.get('city'),
            pincode        = validated_data.get('pincode'),
            payment_method = validated_data.get('payment_method', 'cod'),  # ✅
        )

        total = 0
        for item in cart.items.all():
            if item.product.stock < item.quantity:
                order.delete()
                raise serializers.ValidationError(
                    f"Insufficient stock for '{item.product.name}'. "
                    f"Available: {item.product.stock}, Requested: {item.quantity}"
                )
            OrderItem.objects.create(
                order    = order,
                product  = item.product,
                quantity = item.quantity,
                price    = item.price
            )
            item.product.stock -= item.quantity
            item.product.save()
            total += item.total_price

        discount = 0
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code.upper())
                if coupon.is_valid and total >= coupon.min_order_value:
                    if coupon.type == 'percentage':
                        discount = round((total * coupon.value) / 100, 2)
                    else:
                        discount = min(coupon.value, total)

                    # ✅ Increment usage count
                    coupon.used_count += 1
                    coupon.save()
            except Coupon.DoesNotExist:
                pass

        order.total_amount = round(total - discount, 2)
        order.discount_amount = discount   # ✅ save discount
        order.save()
        cart.items.all().delete()

        return order
    
class CouponSerializer(serializers.ModelSerializer):

    usage_percentage = serializers.SerializerMethodField(read_only=True)
    is_valid         = serializers.ReadOnlyField()

    class Meta:
        model  = Coupon
        fields = [
            'id',
            'code',
            'type',
            'value',
            'max_usage',
            'used_count',
            'usage_percentage',
            'min_order_value',
            'expiry_date',
            'status',
            'is_valid',
            'created_at',
        ]
        read_only_fields = ['used_count', 'created_at']

    def get_usage_percentage(self, obj):
        if obj.max_usage == 0:
            return 0
        return round((obj.used_count / obj.max_usage) * 100, 2)

    def validate_code(self, value):
        # ✅ Always store coupon codes in uppercase
        return value.upper()

    def validate_value(self, value):
        # ✅ Percentage can't exceed 100
        coupon_type = self.initial_data.get('type')
        if coupon_type == 'percentage' and value > 100:
            raise serializers.ValidationError("Percentage discount cannot exceed 100%")
        return value


class ApplyCouponSerializer(serializers.Serializer):
    code        = serializers.CharField()
    cart_total  = serializers.DecimalField(max_digits=10, decimal_places=2)