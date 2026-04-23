from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer
from users.permissions import IsAdminUserRole
from .models import Cart, CartItem, Coupon, Wishlist, Order, OrderItem
from .serializers import CartSerializer, CartItemSerializer, WishlistSerializer, \
      OrderSerializer, OrderItemSerializer, CouponSerializer, ApplyCouponSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, F
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
import razorpay
import hmac
import hashlib
from django.conf import settings

User = get_user_model()

razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

class CartView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)

        return Response(
            {
                "message": "Cart retrieved successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)

        serializer = CartItemSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(cart=cart)
            return Response(
                {
                    "message": "Item added to cart",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"message": "Failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
class CartItemDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def put(self, request, item_id):
        try:
            item = CartItem.objects.get(id=item_id, cart__user=request.user)

            serializer = CartItemSerializer(item, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "message": "Cart item updated",
                        "data": serializer.data
                    },
                    status=status.HTTP_200_OK
                )

            return Response(
                {"message": "Update failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        except CartItem.DoesNotExist:
            return Response(
                {"message": "Item not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, item_id):
        try:
            item = CartItem.objects.get(id=item_id, cart__user=request.user)
            item.delete()

            return Response(
                {"message": "Item removed from cart"},
                status=status.HTTP_204_NO_CONTENT
            )

        except CartItem.DoesNotExist:
            return Response(
                {"message": "Item not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class WishlistView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        wishlist = Wishlist.objects.filter(user=request.user)
        serializer = WishlistSerializer(wishlist, many=True)

        return Response(
            {
                "message": "Wishlist retrieved",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = WishlistSerializer(data={
            "user": request.user.id,
            "product": request.data.get("product")
        })

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Added to wishlist",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"message": "Failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
class WishlistDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, wishlist_id):
        try:
            item = Wishlist.objects.get(id=wishlist_id, user=request.user)
            item.delete()

            return Response(
                {"message": "Removed from wishlist"},
                status=status.HTTP_204_NO_CONTENT
            )

        except Wishlist.DoesNotExist:
            return Response(
                {"message": "Item not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderSerializer(data=request.data, context={'request': request})

        if not serializer.is_valid():
            return Response(
                {"message": "Order failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        order          = serializer.save(user=request.user)
        payment_method = order.payment_method

        # ✅ COD — order placed directly, no Razorpay needed
        if payment_method == 'cod':
            order.payment_status = 'pending'
            order.save()
            return Response(
                {
                    "message": "Order placed successfully (Cash on Delivery)",
                    "data": OrderSerializer(order).data
                },
                status=status.HTTP_201_CREATED
            )

        # ✅ Online — create Razorpay order
        razorpay_order = razorpay_client.order.create({
            "amount":   int(order.total_amount * 100),  # Razorpay needs paise (₹1 = 100 paise)
            "currency": "INR",
            "receipt":  f"order_{order.id}",
            "notes": {
                "order_id": order.id,
                "user":     request.user.email
            }
        })

        # Save Razorpay order ID
        order.razorpay_order_id = razorpay_order['id']
        order.save()

        return Response(
            {
                "message":          "Razorpay order created. Complete payment on frontend.",
                "order_id":         order.id,
                "razorpay_order_id": razorpay_order['id'],
                "amount":           order.total_amount,
                "currency":         "INR",
                "key":              settings.RAZORPAY_KEY_ID,  # send to React
                "data":             OrderSerializer(order).data
            },
            status=status.HTTP_201_CREATED
        )

    def get(self, request):
        orders        = Order.objects.filter(user=request.user).order_by('-created_at')
        serializer    = OrderSerializer(orders, many=True)
        pending_orders = orders.filter(status='pending').count()
        daily_revenue  = orders.filter(created_at__date=datetime.now().date()).aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        return Response(
            {
                "message":       "Orders retrieved",
                "data":          serializer.data,
                "pending_orders": pending_orders,
                "daily_revenue":  daily_revenue
            },
            status=status.HTTP_200_OK
        )


class PaymentVerifyView(APIView):
    """
    Called after Razorpay payment is completed on frontend.
    Verifies the payment signature and marks order as paid.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_order_id   = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature  = request.data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response(
                {"message": "Missing payment details"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Verify signature (prevents fraud)
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()

        if generated_signature != razorpay_signature:
            return Response(
                {"message": "Invalid payment signature. Payment verification failed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Mark order as paid
        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature  = razorpay_signature
            order.payment_status      = 'paid'
            order.status              = 'confirmed'
            order.save()

            return Response(
                {
                    "message": "Payment verified successfully",
                    "data":    OrderSerializer(order).data
                },
                status=status.HTTP_200_OK
            )

        except Order.DoesNotExist:
            return Response(
                {"message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
class OrderDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            serializer = OrderSerializer(order)

            return Response(
                {
                    "message": "Order details",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        except Order.DoesNotExist:
            return Response(
                {"message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
    def delete(self, request, order_id):
        try:
            print("Received request to cancel order with ID:", order_id)
            order = Order.objects.get(id=order_id)
            print("Attempting to cancel order:", order)

            # ✅ Only allow cancelling pending orders
            if order.status != "pending":
                return Response(
                    {"message": "Only pending orders can be cancelled"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ✅ Restore stock for each item
            for item in order.items.all():
                if item.product:
                    item.product.stock += item.quantity
                    item.product.save()

            order.status = "cancelled"
            order.save()

            return Response(
                {"message": "Order cancelled and stock restored"},
                status=status.HTTP_200_OK
            )

        except Order.DoesNotExist:
            return Response(
                {"message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class AdminDashboardView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]
    def get(self, request):

        today = datetime.now().date()
        last_7_days = today - timedelta(days=7)

        total_pending_orders = Order.objects.filter(status='pending').count()
        total_completed_orders = Order.objects.filter(status='completed').count()
        daily_revenue = (Order.objects.filter(created_at__date=today).aggregate(total=Sum('total_amount'))['total'] or 0)

        total_appointments = Appointment.objects.count()
        appointments = Appointment.objects.all()
        appointments_data = AppointmentSerializer(appointments, many=True).data

        total_users = User.objects.count()
        total_orders = Order.objects.count()
        total_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0

        recent_orders = Order.objects.filter(created_at__date__gte=last_7_days).count()

        return Response(
            {
                "message": "Dashboard stats",
                "data": {
                    "total_users": total_users,
                    "total_orders": total_orders,
                    "total_revenue": total_revenue,
                    "orders_last_7_days": recent_orders,
                    "pending_orders": total_pending_orders,
                    "completed_orders": total_completed_orders,
                    "daily_revenue": daily_revenue,
                    "total_appointments": total_appointments,
                    "appointments": appointments_data
                }
            },
            status=status.HTTP_200_OK
        )
    
class AdminOrderListView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]
    def get(self, request):
        orders = Order.objects.all().order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)

        return Response(
            {
                "message": "All orders",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
    
class AdminOrderUpdateStatusView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]
    def patch(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)

            new_status = request.data.get("status")

            if new_status not in dict(Order.STATUS_CHOICES):
                return Response(
                    {"message": "Invalid status"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            order.status = new_status
            order.save()

            return Response(
                {
                    "message": "Order status updated",
                    "data": OrderSerializer(order).data
                },
                status=status.HTTP_200_OK
            )

        except Order.DoesNotExist:
            return Response(
                {"message": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
class AdminSalesAnalyticsView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]
    def get(self, request):

        monthly_sales = (
            Order.objects
            .values('created_at__month')
            .annotate(total_sales=Sum('total_amount'), total_orders=Count('id'))
            .order_by('created_at__month')
        )

        return Response(
            {
                "message": "Sales analytics",
                "data": monthly_sales
            },
            status=status.HTTP_200_OK
        )
    
class AdminUsersView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]
    def get(self, request):

        users = User.objects.all().values('id', 'email', 'role', 'date_joined', 'username', 'first_name', 'last_name').order_by('-date_joined')
        total_users = users.count()

        return Response(
            {
                "message": "Users list",
                "total_users": total_users,
                "data": list(users)
            },
            status=status.HTTP_200_OK
        )

class AdminTopProductsView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]
    def get(self, request):

        top_products = (
            OrderItem.objects
            .values('product__id', 'product__name')
            .annotate(total_sold=Sum('quantity'))
            .order_by('-total_sold')[:10]
        )

        return Response(
            {
                "message": "Top selling products",
                "data": top_products
            },
            status=status.HTTP_200_OK
        )

# ─── Admin: List + Create Coupons ────────────────────────────────────────────
class AdminCouponView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated(), IsAdminUserRole()]
        return [IsAuthenticated(), IsAdminUserRole()]

    def get(self, request):
        coupons = Coupon.objects.all().order_by('-created_at')

        # ✅ Stats for top cards (as shown in your UI)
        total_coupons   = coupons.count()
        active_coupons  = coupons.filter(status='active').count()
        total_redeemed  = coupons.aggregate(total=Sum('used_count'))['total'] or 0
        total_value_saved = Coupon.objects.annotate().aggregate(
            total=Sum('used_count')
        )['total'] or 0

        # ✅ Pagination
        page      = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start     = (page - 1) * page_size
        end       = start + page_size

        serializer = CouponSerializer(coupons[start:end], many=True)

        return Response(
            {
                "message": "Coupons retrieved successfully",
                "stats": {
                    "total_coupons":  total_coupons,
                    "active_coupons": active_coupons,
                    "total_redeemed": total_redeemed,
                },
                "total":    total_coupons,
                "page":     page,
                "pages":    (total_coupons + page_size - 1) // page_size,
                "data":     serializer.data,
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = CouponSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Coupon created successfully",
                    "data":    serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"message": "Coupon creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


# ─── Admin: Get + Update + Delete Single Coupon ───────────────────────────────
class AdminCouponDetailView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get_object(self, coupon_id):
        try:
            return Coupon.objects.get(id=coupon_id)
        except Coupon.DoesNotExist:
            return None

    def get(self, request, coupon_id):
        coupon = self.get_object(coupon_id)
        if not coupon:
            return Response(
                {"message": "Coupon not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = CouponSerializer(coupon)
        return Response(
            {"message": "Coupon details", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def put(self, request, coupon_id):
        coupon = self.get_object(coupon_id)
        if not coupon:
            return Response(
                {"message": "Coupon not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = CouponSerializer(coupon, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Coupon updated successfully", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(
            {"message": "Update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, coupon_id):
        coupon = self.get_object(coupon_id)
        if not coupon:
            return Response(
                {"message": "Coupon not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        coupon.delete()
        return Response(
            {"message": "Coupon deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


# ─── Admin: Toggle Status (Active/Inactive) ───────────────────────────────────
class AdminCouponToggleStatusView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def patch(self, request, coupon_id):
        try:
            coupon        = Coupon.objects.get(id=coupon_id)
            coupon.status = 'inactive' if coupon.status == 'active' else 'active'
            coupon.save()
            return Response(
                {
                    "message": f"Coupon status changed to {coupon.status}",
                    "data":    CouponSerializer(coupon).data
                },
                status=status.HTTP_200_OK
            )
        except Coupon.DoesNotExist:
            return Response(
                {"message": "Coupon not found"},
                status=status.HTTP_404_NOT_FOUND
            )


# ─── Customer: Apply Coupon at Checkout ──────────────────────────────────────
class ApplyCouponView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Invalid data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        code       = serializer.validated_data['code'].upper()
        cart_total = serializer.validated_data['cart_total']

        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return Response(
                {"message": "Invalid coupon code"},
                status=status.HTTP_404_NOT_FOUND
            )

        # ✅ Validations
        if not coupon.is_valid:
            return Response(
                {"message": "Coupon is expired or inactive"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if cart_total < coupon.min_order_value:
            return Response(
                {
                    "message": f"Minimum order value for this coupon is ₹{coupon.min_order_value}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Calculate discount
        if coupon.type == 'percentage':
            discount = round((cart_total * coupon.value) / 100, 2)
        else:
            discount = min(coupon.value, cart_total)  # fixed can't exceed cart total

        final_total = round(cart_total - discount, 2)

        return Response(
            {
                "message":     "Coupon applied successfully",
                "code":        coupon.code,
                "type":        coupon.type,
                "discount":    discount,
                "cart_total":  cart_total,
                "final_total": final_total,
            },
            status=status.HTTP_200_OK
        )