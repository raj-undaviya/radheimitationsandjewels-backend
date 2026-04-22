from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer
from users.permissions import IsAdminUserRole
from .serializers import OrderSerializer
from .models import Cart, CartItem, Wishlist, Order, OrderItem
from .serializers import CartSerializer, CartItemSerializer, WishlistSerializer, OrderSerializer, OrderItemSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, F
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta

User = get_user_model()

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

        if serializer.is_valid():
            serializer.save(user=request.user)

            return Response(
                {
                    "message": "Order placed successfully",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"message": "Order failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    permission_classes = [IsAuthenticated]
    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        pending_orders = orders.filter(status='pending').count()
        daily_revenue = orders.filter(created_at__date=datetime.now().date()).aggregate(total=Sum('total_amount'))['total'] or 0

        return Response(
            {
                "message": "Orders retrieved",
                "data": serializer.data,
                "pending_orders": pending_orders,
                "daily_revenue": daily_revenue
            },
            status=status.HTTP_200_OK
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

        users = User.objects.all().values('id', 'email', 'role', 'date_joined').order_by('-date_joined')
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