
# Django Import
from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Category, Brand, Product
from .serializers import CategorySerializer, BrandSerializer, ProductSerializer, BarcodeCheckSerializer
from .permissions import IsManagerOrReadOnly, IsInventoryStaffOrReadOnly, IsOwnerOrManager

# Python Import


class CategoryViewSet(viewsets.ModelViewSet):

    queryset = Category.objects.all().order_by('name') # Order categories by name by default
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrReadOnly] # Example permission: Read-only for unauthenticated, authenticated users can do more
    authentication_classes = [JWTAuthentication]



class BrandViewSet(viewsets.ModelViewSet):

    queryset = Brand.objects.all().order_by('name')
    serializer_class = BrandSerializer
    permission_classes = [IsManagerOrReadOnly]
    authentication_classes = [JWTAuthentication]
    # Optionally, customize actions if needed


class ProductViewSet(viewsets.ModelViewSet):

    queryset = Product.objects.all().order_by('name')
    serializer_class = ProductSerializer
    permission_classes = [IsInventoryStaffOrReadOnly] # Permissions will be refined later
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] # Add filter backends

    filterset_fields = {
        'category': ['exact'],
        'brand': ['exact'],
        'is_active': ['exact'],
        'stock_quantity': ['exact', 'gt', 'gte', 'lt', 'lte'],
    } # Fields available for filtering

    search_fields = ['name', 'sku', 'description', 'barcode'] # Fields available for searching

    ordering_fields = ['name', 'selling_price', 'created_at', 'stock_quantity'] # Fields available for ordering
    ordering = ['name'] # Default ordering


class BarcodeCheckView(APIView):

    def post(self, request):
        serializer = BarcodeCheckSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"is_unique": True}, status=status.HTTP_200_OK)
        return Response({"is_unique": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)