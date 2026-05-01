import razorpay, hmac, hashlib, csv, io
from datetime import datetime, timedelta, date
from django.db.models import Sum, Count, F, Avg
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer
from users.permissions import IsAdminUserRole
from .models import Cart, CartItem, Coupon, Wishlist, Order, OrderItem
from .serializers import CartSerializer, CartItemSerializer, WishlistSerializer, \
      OrderSerializer, OrderItemSerializer, CouponSerializer, ApplyCouponSerializer
from decimal import Decimal

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

        users = User.objects.all().values('id', 'email', 'role', 'date_joined', 'username', 'first_name', 'last_name', 'phonenumber', 'profile_image').order_by('-date_joined')
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
        coupon.status = 'inactive'  # ✅ Soft delete by marking as inactive
        coupon.save()
        # coupon.delete()
        return Response(
            {"message": "Coupon marked as inactive successfully"},
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

class SalesPerformanceView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        filter_type  = request.query_params.get('filter', 'this_month')  # default
        start_date   = request.query_params.get('start_date', None)      # for custom
        end_date     = request.query_params.get('end_date', None)        # for custom

        today = timezone.now().date()

        # ✅ Determine date range based on filter
        if filter_type == 'daily':
            start    = today
            end      = today
            trunc_by = TruncDate

        elif filter_type == 'this_month':
            start    = today.replace(day=1)
            end      = today
            trunc_by = TruncDate

        elif filter_type == 'last_3_months':
            start    = today - timedelta(days=90)
            end      = today
            trunc_by = TruncDate

        elif filter_type == 'last_6_months':
            start    = today - timedelta(days=180)
            end      = today
            trunc_by = TruncMonth

        elif filter_type == 'this_year':
            start    = today.replace(month=1, day=1)
            end      = today
            trunc_by = TruncMonth

        elif filter_type == 'custom':
            if not start_date or not end_date:
                return Response(
                    {"message": "Provide start_date and end_date for custom filter (YYYY-MM-DD)"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end   = datetime.strptime(end_date,   '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"message": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # auto pick grouping based on range
            delta = (end - start).days
            if delta <= 31:
                trunc_by = TruncDate
            elif delta <= 180:
                trunc_by = TruncDate
            else:
                trunc_by = TruncMonth

        else:
            return Response(
                {"message": "Invalid filter. Use: daily, this_month, last_3_months, last_6_months, this_year, custom"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Query — Revenue (orange solid line)
        revenue_data = (
            Order.objects
            .filter(created_at__date__gte=start, created_at__date__lte=end)
            .annotate(period=trunc_by('created_at'))
            .values('period')
            .annotate(revenue=Sum('total_amount'))
            .order_by('period')
        )

        # ✅ Query — Orders count (grey dashed line)
        orders_data = (
            Order.objects
            .filter(created_at__date__gte=start, created_at__date__lte=end)
            .annotate(period=trunc_by('created_at'))
            .values('period')
            .annotate(orders=Count('id'))
            .order_by('period')
        )

        # ✅ Merge both into one chart-ready list
        revenue_map = {
            str(item['period'].strftime('%Y-%m-%d') if hasattr(item['period'], 'strftime') else item['period']): float(item['revenue'] or 0)
            for item in revenue_data
        }
        orders_map = {
            str(item['period'].strftime('%Y-%m-%d') if hasattr(item['period'], 'strftime') else item['period']): item['orders']
            for item in orders_data
        }

        # ✅ Build combined data points
        all_periods = sorted(set(list(revenue_map.keys()) + list(orders_map.keys())))

        chart_data = [
            {
                "period":  period,
                "revenue": revenue_map.get(period, 0),   # orange solid line
                "orders":  orders_map.get(period, 0),    # grey dashed line
            }
            for period in all_periods
        ]

        # ✅ Summary stats for the selected period
        total_revenue = sum(item['revenue'] for item in chart_data)
        total_orders  = sum(item['orders']  for item in chart_data)
        avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0

        # ✅ Previous period comparison (for % change)
        period_days   = (end - start).days or 1
        prev_start    = start - timedelta(days=period_days)
        prev_end      = start - timedelta(days=1)

        prev_revenue = (
            Order.objects
            .filter(created_at__date__gte=prev_start, created_at__date__lte=prev_end)
            .aggregate(total=Sum('total_amount'))['total'] or 0
        )

        revenue_change = 0
        if prev_revenue > 0:
            revenue_change = round(((total_revenue - float(prev_revenue)) / float(prev_revenue)) * 100, 2)

        return Response(
            {
                "message": "Sales performance data",
                "filter":  filter_type,
                "period": {
                    "start": str(start),
                    "end":   str(end),
                },
                "summary": {
                    "total_revenue":    round(total_revenue, 2),
                    "total_orders":     total_orders,
                    "avg_order_value":  avg_order_value,
                    "revenue_change":   revenue_change,   # % vs previous period
                },
                "chart_data": chart_data,   # ✅ feed this directly to your chart
            },
            status=status.HTTP_200_OK
        )
    
def get_date_range(period):
    today = timezone.now().date()

    if period == 'current_month':
        start = today.replace(day=1)
        end   = today
    elif period == 'last_30_days':
        start = today - timedelta(days=30)
        end   = today
    elif period == 'last_3_months':
        start = today - timedelta(days=90)
        end   = today
    elif period == 'last_6_months':
        start = today - timedelta(days=180)
        end   = today
    elif period == 'this_year':
        start = today.replace(month=1, day=1)
        end   = today
    else:
        start = today - timedelta(days=30)
        end   = today

    return start, end


# ─── Helper: Currency multiplier ──────────────────────────────────────────────
def get_currency_multiplier(currency):
    # Simple static rates — replace with live API if needed
    rates = {
        'INR': 1,
        'USD': 0.012,
        'EUR': 0.011,
        'GBP': 0.0095,
    }
    return rates.get(currency, 1)


# ─── 1. Performance Report Summary (Top Cards) ───────────────────────────────
class PerformanceReportView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        period   = request.query_params.get('period', 'last_30_days')
        currency = request.query_params.get('currency', 'INR')

        start, end    = get_date_range(period)
        multiplier    = get_currency_multiplier(currency)

        # Previous period for growth comparison
        delta      = (end - start).days or 1
        prev_start = start - timedelta(days=delta)
        prev_end   = start - timedelta(days=1)

        # ✅ Current period
        current_orders  = Order.objects.filter(
            created_at__date__gte=start,
            created_at__date__lte=end
        )
        total_sales     = float(current_orders.aggregate(t=Sum('total_amount'))['t'] or 0) * multiplier
        total_orders    = current_orders.count()
        avg_order_value = float(current_orders.aggregate(a=Avg('total_amount'))['a'] or 0) * multiplier

        # ✅ Previous period
        prev_orders      = Order.objects.filter(
            created_at__date__gte=prev_start,
            created_at__date__lte=prev_end
        )
        prev_sales       = float(prev_orders.aggregate(t=Sum('total_amount'))['t'] or 0) * multiplier
        prev_avg         = float(prev_orders.aggregate(a=Avg('total_amount'))['a'] or 0) * multiplier

        # ✅ Growth rate
        growth_rate = 0
        if prev_sales > 0:
            growth_rate = round(((total_sales - prev_sales) / prev_sales) * 100, 1)

        avg_change = 0
        if prev_avg > 0:
            avg_change = round(((avg_order_value - prev_avg) / prev_avg) * 100, 1)

        # ✅ Avg order value trend
        avg_trend = "stable"
        if avg_change > 5:
            avg_trend = "up"
        elif avg_change < -5:
            avg_trend = "down"

        return Response(
            {
                "message": "Performance report",
                "period":  {"start": str(start), "end": str(end)},
                "currency": currency,
                "data": {
                    "total_sales": {
                        "value":  round(total_sales, 2),
                        "change": growth_rate,          # e.g. +12.4%
                        "trend":  "up" if growth_rate >= 0 else "down"
                    },
                    "growth_rate": {
                        "value":  growth_rate,          # e.g. 18.5%
                        "change": round(growth_rate - (prev_sales / max(prev_sales, 1) * 100), 1),
                        "trend":  "up" if growth_rate >= 0 else "down"
                    },
                    "avg_order_value": {
                        "value":  round(avg_order_value, 2),
                        "change": avg_change,
                        "trend":  avg_trend             # "stable" / "up" / "down"
                    },
                }
            },
            status=status.HTTP_200_OK
        )


# ─── 2. Sales Analytics Report (Generate + Download) ─────────────────────────
class SalesAnalyticsReportView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        period      = request.query_params.get('period', 'current_month')
        category_id = request.query_params.get('category', None)
        currency    = request.query_params.get('currency', 'INR')
        download    = request.query_params.get('download', None)   # 'csv' or 'pdf'

        start, end   = get_date_range(period)
        multiplier   = get_currency_multiplier(currency)

        # ✅ Base queryset
        orders = Order.objects.filter(
            created_at__date__gte=start,
            created_at__date__lte=end
        )

        # ✅ Filter by category if provided
        if category_id:
            orders = orders.filter(items__product__category__id=category_id)

        # ✅ Build report rows
        report_data = (
            orders
            .annotate(period=TruncDate('created_at'))
            .values('period')
            .annotate(
                total_revenue = Sum('total_amount'),
                total_orders  = Count('id'),
                avg_value     = Avg('total_amount')
            )
            .order_by('period')
        )

        rows = [
            {
                "date":          str(item['period']),
                "total_revenue": round(float(item['total_revenue'] or 0) * multiplier, 2),
                "total_orders":  item['total_orders'],
                "avg_value":     round(float(item['avg_value'] or 0) * multiplier, 2),
                "currency":      currency,
            }
            for item in report_data
        ]

        # ✅ Download CSV
        if download == 'csv':
            return self._download_csv(rows, currency)

        # ✅ Download PDF
        if download == 'pdf':
            return self._download_pdf(rows, currency, start, end)

        # ✅ JSON response
        return Response(
            {
                "message":    "Sales analytics report",
                "period":     {"start": str(start), "end": str(end)},
                "currency":   currency,
                "total_rows": len(rows),
                "data":       rows,
            },
            status=status.HTTP_200_OK
        )

    def _download_csv(self, rows, currency):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Date', f'Total Revenue ({currency})', 'Total Orders', f'Avg Order Value ({currency})'])

        for row in rows:
            writer.writerow([
                row['date'],
                row['total_revenue'],
                row['total_orders'],
                row['avg_value'],
            ])

        return response

    def _download_pdf(self, rows, currency, start, end):
        buffer   = io.BytesIO()
        doc      = SimpleDocTemplate(buffer, pagesize=letter)
        styles   = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph("Sales Analytics Report", styles['Title']))
        elements.append(Paragraph(f"Period: {start} to {end} | Currency: {currency}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Table
        table_data = [[
            'Date',
            f'Revenue ({currency})',
            'Orders',
            f'Avg Value ({currency})'
        ]]
        for row in rows:
            table_data.append([
                row['date'],
                str(row['total_revenue']),
                str(row['total_orders']),
                str(row['avg_value']),
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F97316')),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFF7ED')]),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE',   (0, 0), (-1, -1), 9),
            ('PADDING',    (0, 0), (-1, -1), 6),
        ]))

        elements.append(table)
        doc.build(elements)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
        return response


# ─── 3. Order Processing Report ───────────────────────────────────────────────
class OrderProcessingReportView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        period   = request.query_params.get('period', 'last_30_days')
        download = request.query_params.get('download', None)

        start, end = get_date_range(period)

        # ✅ Pending fulfillment
        pending_orders = Order.objects.filter(
            status='pending'
        )
        pending_count = pending_orders.count()

        # ✅ Return requests (cancelled orders)
        return_requests = Order.objects.filter(
            status='cancelled',
            created_at__date__gte=start,
            created_at__date__lte=end
        ).count()

        # ✅ Detailed pending orders list
        pending_list = Order.objects.filter(status='pending').values(
            'id',
            'user__email',
            'total_amount',
            'payment_method',
            'created_at',
            'city',
        ).order_by('-created_at')[:50]

        rows = list(pending_list)

        if download == 'csv':
            return self._download_csv(rows)

        if download == 'pdf':
            return self._download_pdf(rows, start, end)

        return Response(
            {
                "message": "Order processing report",
                "period":  {"start": str(start), "end": str(end)},
                "data": {
                    "pending_fulfillment": {
                        "count": pending_count,
                        "label": f"{pending_count} Orders"
                    },
                    "return_requests": {
                        "count": return_requests,
                        "label": f"{return_requests} Cases"
                    },
                },
                "pending_orders": rows
            },
            status=status.HTTP_200_OK
        )

    def _download_csv(self, rows):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="order_processing_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Order ID', 'Customer Email', 'Total Amount', 'Payment Method', 'City', 'Created At'])
        for row in rows:
            writer.writerow([
                row['id'],
                row['user__email'],
                row['total_amount'],
                row['payment_method'],
                row['city'],
                str(row['created_at']),
            ])
        return response

    def _download_pdf(self, rows, start, end):
        buffer   = io.BytesIO()
        doc      = SimpleDocTemplate(buffer, pagesize=letter)
        styles   = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Order Processing Report", styles['Title']))
        elements.append(Paragraph(f"Period: {start} to {end}", styles['Normal']))
        elements.append(Spacer(1, 20))

        table_data = [['Order ID', 'Customer', 'Amount', 'Payment', 'City']]
        for row in rows:
            table_data.append([
                str(row['id']),
                str(row['user__email']),
                str(row['total_amount']),
                str(row['payment_method']),
                str(row['city']),
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F97316')),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFF7ED')]),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE',   (0, 0), (-1, -1), 9),
            ('PADDING',    (0, 0), (-1, -1), 6),
        ]))

        elements.append(table)
        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="order_processing_report.pdf"'
        return response


# ─── 4. Client Insights Report ────────────────────────────────────────────────
class ClientInsightsReportView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        period   = request.query_params.get('period', 'last_30_days')
        download = request.query_params.get('download', None)

        start, end   = get_date_range(period)
        delta        = (end - start).days or 1
        prev_start   = start - timedelta(days=delta)
        prev_end     = start - timedelta(days=1)

        # ✅ High Net Worth Clients — users who spent > ₹10,000 total
        HNW_THRESHOLD = 10000

        hnw_current = (
            User.objects
            .annotate(total_spent=Sum('orders__total_amount'))
            .filter(
                total_spent__gte=HNW_THRESHOLD,
                orders__created_at__date__gte=start,
                orders__created_at__date__lte=end
            )
            .distinct()
            .count()
        )

        hnw_prev = (
            User.objects
            .annotate(total_spent=Sum('orders__total_amount'))
            .filter(
                total_spent__gte=HNW_THRESHOLD,
                orders__created_at__date__gte=prev_start,
                orders__created_at__date__lte=prev_end
            )
            .distinct()
            .count()
        )

        hnw_new = hnw_current - hnw_prev

        # ✅ Retention Rate
        # Users who ordered in previous period AND current period
        prev_buyers = set(
            Order.objects
            .filter(created_at__date__gte=prev_start, created_at__date__lte=prev_end)
            .values_list('user_id', flat=True)
        )
        current_buyers = set(
            Order.objects
            .filter(created_at__date__gte=start, created_at__date__lte=end)
            .values_list('user_id', flat=True)
        )

        retained       = len(prev_buyers & current_buyers)
        retention_rate = round((retained / max(len(prev_buyers), 1)) * 100, 1)

        # ✅ Top clients list
        top_clients = (
            User.objects
            .annotate(
                total_spent  = Sum('orders__total_amount'),
                total_orders = Count('orders')
            )
            .filter(total_spent__isnull=False)
            .order_by('-total_spent')[:20]
            .values('id', 'email', 'total_spent', 'total_orders')
        )

        rows = list(top_clients)

        if download == 'csv':
            return self._download_csv(rows)

        if download == 'pdf':
            return self._download_pdf(rows, start, end, retention_rate)

        return Response(
            {
                "message": "Client insights report",
                "period":  {"start": str(start), "end": str(end)},
                "data": {
                    "high_net_worth_clients": {
                        "count": hnw_current,
                        "new":   f"+{hnw_new} New" if hnw_new >= 0 else str(hnw_new)
                    },
                    "retention_rate": {
                        "value": retention_rate,
                        "label": f"{retention_rate}%"
                    },
                },
                "top_clients": rows
            },
            status=status.HTTP_200_OK
        )

    def _download_csv(self, rows):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="client_insights_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Customer Email', 'Total Spent (INR)', 'Total Orders'])
        for row in rows:
            writer.writerow([
                row['email'],
                row['total_spent'],
                row['total_orders'],
            ])
        return response

    def _download_pdf(self, rows, start, end, retention_rate):
        buffer   = io.BytesIO()
        doc      = SimpleDocTemplate(buffer, pagesize=letter)
        styles   = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Client Insights Report", styles['Title']))
        elements.append(Paragraph(f"Period: {start} to {end} | Retention Rate: {retention_rate}%", styles['Normal']))
        elements.append(Spacer(1, 20))

        table_data = [['Email', 'Total Spent (INR)', 'Total Orders']]
        for row in rows:
            table_data.append([
                str(row['email']),
                str(row['total_spent']),
                str(row['total_orders']),
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F97316')),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFF7ED')]),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE',   (0, 0), (-1, -1), 9),
            ('PADDING',    (0, 0), (-1, -1), 6),
        ]))

        elements.append(table)
        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="client_insights_report.pdf"'
        return response

class PaymentStatsView(APIView):
    """
    GET /api/payments/stats/
    Summary cards: Total Revenue, Today's Collections, Pending Transactions, Success Rate
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()

        # Total Revenue (all paid orders)
        total_revenue = Order.objects.filter(
            payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        # Today's Collections
        todays_collections = Order.objects.filter(
            payment_status='paid',
            created_at__date=today
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        # Pending Transactions count
        pending_count = Order.objects.filter(
            payment_status='pending',
            payment_method='online'
        ).count()

        # Success Rate
        total_online = Order.objects.filter(payment_method='online').count()
        total_paid   = Order.objects.filter(
            payment_method='online',
            payment_status='paid'
        ).count()

        success_rate = (
            round((total_paid / total_online) * 100, 1)
            if total_online > 0 else 0
        )

        return Response({
            "total_revenue":       total_revenue,
            "todays_collections":  todays_collections,
            "pending_transactions": pending_count,
            "success_rate":        success_rate,
        })


class PaymentListView(APIView):
    """
    GET /api/payments/
    Query params:
        - days        : 7 | 30 | 90 | all  (default: 30)
        - method      : cod | online
        - status      : pending | paid | failed | refunded
        - page        : page number (default: 1)
        - page_size   : results per page (default: 10)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Order.objects.select_related('user').order_by('-created_at')

        # ── Filters ───────────────────────────────────────────────────────
        days = request.query_params.get('days', '30')
        if days != 'all':
            try:
                delta = timedelta(days=int(days))
                qs = qs.filter(created_at__gte=timezone.now() - delta)
            except ValueError:
                pass

        method = request.query_params.get('method')
        if method:
            qs = qs.filter(payment_method=method)

        status = request.query_params.get('status')
        if status:
            qs = qs.filter(payment_status=status)

        # ── Pagination ────────────────────────────────────────────────────
        try:
            page      = max(1, int(request.query_params.get('page', 1)))
            page_size = max(1, int(request.query_params.get('page_size', 10)))
        except ValueError:
            page, page_size = 1, 10

        total   = qs.count()
        start   = (page - 1) * page_size
        end     = start + page_size
        orders  = qs[start:end]

        data = []
        for order in orders:
            data.append({
                "order_id":         f"#RJ-{order.id}",
                "customer_name":    order.user.get_full_name() or order.user.username,
                "customer_avatar":  order.user.profile_image,
                "date":             order.created_at,
                "payment_method":   order.payment_method,
                "amount":           order.total_amount,
                "payment_status":   order.payment_status,
                "order_status":     order.status,
            })

        return Response({
            "count":     total,
            "page":      page,
            "page_size": page_size,
            "pages":     (total + page_size - 1) // page_size,
            "results":   data,
        })


class PaymentDetailView(APIView):
    """
    GET /api/payments/<order_id>/
    Transaction detail modal data
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.select_related('user').prefetch_related('items__product').get(id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Transaction not found."}, status=404)

        user = order.user

        items = []
        for item in order.items.all():
            items.append({
                "product_name": item.product.name if item.product else "Deleted Product",
                "quantity":     item.quantity,
                "price":        item.price,
                "total":        item.total_price,
            })

        return Response({
            "reference":        f"#RJ-{order.id}",
            "amount":           order.total_amount,
            "discount_amount":  order.discount_amount,
            "status":           order.payment_status,
            "order_status":     order.status,
            "date":             order.created_at,

            "customer": {
                "name":         user.get_full_name() or user.username,
                "email":        user.email,
                "phone":        user.phonenumber,
                "profile_image": user.profile_image,
            },

            "payment_info": {
                "method":               order.payment_method,
                "razorpay_order_id":    order.razorpay_order_id,
                "razorpay_payment_id":  order.razorpay_payment_id,
            },

            "billing_address": {
                "address": order.address,
                "city":    order.city,
                "pincode": order.pincode,
            },

            "items": items,
        })


class PaymentExportView(APIView):
    """
    GET /api/payments/export/
    Returns all payment records as CSV-ready list
    Same filters as PaymentListView
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import csv
        from django.http import HttpResponse

        qs = Order.objects.select_related('user').order_by('-created_at')

        days = request.query_params.get('days', '30')
        if days != 'all':
            try:
                delta = timedelta(days=int(days))
                qs = qs.filter(created_at__gte=timezone.now() - delta)
            except ValueError:
                pass

        method = request.query_params.get('method')
        if method:
            qs = qs.filter(payment_method=method)

        status = request.query_params.get('status')
        if status:
            qs = qs.filter(payment_status=status)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Order ID', 'Customer Name', 'Email', 'Phone',
            'Date', 'Payment Method', 'Amount',
            'Discount', 'Payment Status', 'Order Status',
            'Razorpay Order ID', 'Razorpay Payment ID',
        ])

        for order in qs:
            writer.writerow([
                f"#RJ-{order.id}",
                order.user.get_full_name() or order.user.username,
                order.user.email,
                order.user.phonenumber,
                order.created_at.strftime('%b %d, %Y %H:%M'),
                order.payment_method,
                order.total_amount,
                order.discount_amount,
                order.payment_status,
                order.status,
                order.razorpay_order_id or '',
                order.razorpay_payment_id or '',
            ])

        return response