from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from appointments.serializers import AppointmentSerializer
from appointments.models import Appointment
from products.models import Product, Category, SubCategory
from orders.models import Order
from products.serializers import ProductSerializer, CategorySerializer, SubCategorySerializer
from orders.serializers import OrderSerializer

from .serializers import GlobalSearchSerializer


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query      = request.query_params.get('q', '').strip()
        min_price  = request.query_params.get('min_price')
        max_price  = request.query_params.get('max_price')

        if not query and not min_price and not max_price:
            return Response({"detail": "Please provide a search query 'q'."}, status=400)

        results = {
            "query":        query,
            "products":     [],
            "categories":   [],
            "subcategories":[],
            "orders":       [],
            "appointments": [],
        }

        # ── Products ──────────────────────────────────────────────────────
        product_qs = Product.objects.select_related(
            'category', 'subcategory'
        ).prefetch_related('images')

        if query:
            product_qs = product_qs.filter(
                Q(name__icontains=query)          |
                Q(description__icontains=query)   |
                Q(sku__icontains=query)            |
                Q(tags__icontains=query)           |
                Q(category__name__icontains=query) |
                Q(subcategory__name__icontains=query)
            )

        if min_price:
            product_qs = product_qs.filter(price__gte=min_price)
        if max_price:
            product_qs = product_qs.filter(price__lte=max_price)

        results["products"] = ProductSerializer(
            product_qs, many=True, context={'request': request}
        ).data

        # ── Categories ────────────────────────────────────────────────────
        if query:
            category_qs = Category.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
            results["categories"] = CategorySerializer(
                category_qs, many=True, context={'request': request}
            ).data

        # ── SubCategories ─────────────────────────────────────────────────
        if query:
            subcategory_qs = SubCategory.objects.select_related('category').filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
            results["subcategories"] = SubCategorySerializer(
                subcategory_qs, many=True, context={'request': request}
            ).data

        # ── Orders ────────────────────────────────────────────────────────
        if query:
            order_qs = Order.objects.filter(user=request.user).filter(
                Q(status__icontains=query)          |
                Q(items__product__name__icontains=query) |
                Q(address__icontains=query)         |
                Q(city__icontains=query)
            ).distinct()
            results["orders"] = OrderSerializer(
                order_qs, many=True, context={'request': request}
            ).data

        # ── Appointments ──────────────────────────────────────────────────
        if query:
            appointment_qs = Appointment.objects.filter(user=request.user).filter(
                Q(status__icontains=query)       |
                Q(service__icontains=query)      |
                Q(notes__icontains=query)
            )
            results["appointments"] = AppointmentSerializer(
                appointment_qs, many=True, context={'request': request}
            ).data

        return Response(results)