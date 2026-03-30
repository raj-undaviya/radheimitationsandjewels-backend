from .serializers import OrderSerializer
from .models import Cart, CartItem, Wishlist, Order, OrderItem
from .serializers import CartSerializer, CartItemSerializer, WishlistSerializer, OrderSerializer, OrderItemSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

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

    def get(self, request):
        orders = Order.objects.filter(user=request.user)
        serializer = OrderSerializer(orders, many=True)

        return Response(
            {
                "message": "Orders retrieved",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

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