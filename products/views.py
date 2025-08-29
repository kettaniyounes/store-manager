# Django Import
from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.core.files.base import ContentFile
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q, Sum, F, Case, When, DecimalField
from django.utils import timezone
from datetime import timedelta
from .models import (
    Category, Brand, Product, ProductImage, ProductVariant,
    StockMovement, StockAdjustment, ProductExpiration
)
from .serializers import (
    CategorySerializer, BrandSerializer, ProductImageSerializer, ProductSerializer, 
    BarcodeCheckSerializer, ProductVariantSerializer, StockMovementSerializer,
    StockAdjustmentSerializer, ProductExpirationSerializer, LowStockReportSerializer,
    ReorderReportSerializer, InventoryValuationSerializer
)
from .permissions import IsManagerOrReadOnly, IsInventoryStaffOrReadOnly, IsOwnerOrManager

# Python Import
import base64



class CategoryViewSet(viewsets.ModelViewSet):

    queryset = Category.objects.all().order_by('name') # Order categories by name by default
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrReadOnly] # Example permission: Read-only for unauthenticated, authenticated users can do more
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    search_fields = ['name']



class BrandViewSet(viewsets.ModelViewSet):

    queryset = Brand.objects.all().order_by('name')
    serializer_class = BrandSerializer
    permission_classes = [IsManagerOrReadOnly]
    authentication_classes = [JWTAuthentication]
    # Optionally, customize actions if needed


class ProductPagination(PageNumberPagination): # Define a custom pagination class
    page_size = 20  # Default page size
    page_size_query_param = 'page_size' # Allow client to set page size using 'page_size' query param
    max_page_size = 100 # Maximum page size that can be requested

class ProductViewSet(viewsets.ModelViewSet):

    queryset = Product.objects.all().order_by('name')
    serializer_class = ProductSerializer
    permission_classes = [IsInventoryStaffOrReadOnly] # Permissions will be refined later
    authentication_classes = [JWTAuthentication]
    pagination_class = ProductPagination # Set the pagination class for ProductViewSet # Permissions will be refined later

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] # Add filter backends

    filterset_fields = {
        'category': ['exact'],
        'brand': ['exact'],
        'is_active': ['exact'],
        'stock_quantity': ['exact', 'gt', 'gte', 'lt', 'lte'],
        'is_perishable': ['exact'],
        'inventory_valuation_method': ['exact'],
    } # Fields available for filtering

    search_fields = ['name', 'sku', 'description', 'barcode'] # Fields available for searching

    ordering_fields = ['name', 'selling_price', 'created_at', 'stock_quantity', 'reorder_point'] # Fields available for ordering
    ordering = ['name'] # Default ordering

    @action(detail=False, methods=['get'])
    def low_stock_report(self, request):
        """Get products that are below low stock threshold"""
        low_stock_products = self.get_queryset().filter(
            stock_quantity__lte=F('low_stock_threshold'),
            is_active=True
        ).select_related('category', 'brand')
        
        serializer = LowStockReportSerializer(low_stock_products, many=True)
        return Response({
            'count': low_stock_products.count(),
            'products': serializer.data
        })

    @action(detail=False, methods=['get'])
    def reorder_report(self, request):
        """Get products that need to be reordered"""
        reorder_products = self.get_queryset().filter(
            stock_quantity__lte=F('reorder_point'),
            is_active=True
        ).select_related('category', 'brand')
        
        serializer = ReorderReportSerializer(reorder_products, many=True)
        total_estimated_cost = sum(
            product.reorder_quantity * product.cost_price 
            for product in reorder_products
        )
        
        return Response({
            'count': reorder_products.count(),
            'total_estimated_cost': total_estimated_cost,
            'products': serializer.data
        })

    @action(detail=False, methods=['get'])
    def inventory_valuation(self, request):
        """Get inventory valuation report"""
        products = self.get_queryset().filter(
            stock_quantity__gt=0,
            is_active=True
        ).select_related('category', 'brand')
        
        serializer = InventoryValuationSerializer(products, many=True)
        
        # Calculate totals
        total_cost_value = sum(
            product.stock_quantity * product.average_cost 
            for product in products
        )
        total_selling_value = sum(
            product.stock_quantity * product.selling_price 
            for product in products
        )
        potential_profit = total_selling_value - total_cost_value
        
        return Response({
            'summary': {
                'total_products': products.count(),
                'total_cost_value': total_cost_value,
                'total_selling_value': total_selling_value,
                'potential_profit': potential_profit,
                'profit_margin_percentage': (potential_profit / total_cost_value * 100) if total_cost_value > 0 else 0
            },
            'products': serializer.data
        })

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """Manually adjust stock quantity for a product"""
        product = self.get_object()
        quantity_after = request.data.get('quantity_after')
        reason = request.data.get('reason', 'system_error')
        notes = request.data.get('notes', '')
        
        if quantity_after is None:
            return Response(
                {'error': 'quantity_after is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity_after = int(quantity_after)
            if quantity_after < 0:
                return Response(
                    {'error': 'quantity_after cannot be negative'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'quantity_after must be a valid integer'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create stock adjustment record
        adjustment = StockAdjustment.objects.create(
            product=product,
            reason=reason,
            quantity_before=product.stock_quantity,
            quantity_after=quantity_after,
            unit_cost=product.average_cost,
            notes=notes,
            user=request.user
        )
        
        # Create stock movement record
        adjustment_quantity = quantity_after - product.stock_quantity
        StockMovement.objects.create(
            product=product,
            movement_type='adjustment',
            quantity=adjustment_quantity,
            unit_cost=product.average_cost,
            reference_id=adjustment.adjustment_id,
            notes=f"Stock adjustment: {reason}",
            user=request.user
        )
        
        # Update product stock quantity
        product.stock_quantity = quantity_after
        product.save(update_fields=['stock_quantity'])
        
        serializer = StockAdjustmentSerializer(adjustment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StockMovementViewSet(viewsets.ModelViewSet):
    """ViewSet for managing stock movements"""
    
    queryset = StockMovement.objects.all().order_by('-movement_date')
    serializer_class = StockMovementSerializer
    permission_classes = [IsInventoryStaffOrReadOnly]
    authentication_classes = [JWTAuthentication]
    pagination_class = ProductPagination
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'product': ['exact'],
        'movement_type': ['exact'],
        'movement_date': ['date', 'date__gte', 'date__lte'],
        'user': ['exact'],
    }
    
    search_fields = ['product__name', 'product__sku', 'reference_id', 'notes']
    ordering_fields = ['movement_date', 'quantity', 'total_cost']
    ordering = ['-movement_date']
    
    def perform_create(self, serializer):
        """Automatically update product stock when creating stock movement"""
        movement = serializer.save(user=self.request.user)
        
        # Update product stock quantity
        product = movement.product
        if movement.movement_type in ['purchase', 'return', 'adjustment']:
            # Stock in movements
            product.stock_quantity += abs(movement.quantity)
        elif movement.movement_type in ['sale', 'damage', 'expired', 'transfer']:
            # Stock out movements
            product.stock_quantity -= abs(movement.quantity)
            if product.stock_quantity < 0:
                product.stock_quantity = 0
        
        product.save(update_fields=['stock_quantity'])


class StockAdjustmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing stock adjustments"""
    
    queryset = StockAdjustment.objects.all().order_by('-adjustment_date')
    serializer_class = StockAdjustmentSerializer
    permission_classes = [IsInventoryStaffOrReadOnly]
    authentication_classes = [JWTAuthentication]
    pagination_class = ProductPagination
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'product': ['exact'],
        'reason': ['exact'],
        'adjustment_date': ['date', 'date__gte', 'date__lte'],
        'user': ['exact'],
    }
    
    search_fields = ['product__name', 'product__sku', 'notes']
    ordering_fields = ['adjustment_date', 'adjustment_quantity', 'total_value_impact']
    ordering = ['-adjustment_date']
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ProductExpirationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing product expiration tracking"""
    
    queryset = ProductExpiration.objects.all().order_by('expiration_date')
    serializer_class = ProductExpirationSerializer
    permission_classes = [IsInventoryStaffOrReadOnly]
    authentication_classes = [JWTAuthentication]
    pagination_class = ProductPagination
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'product': ['exact'],
        'is_expired': ['exact'],
        'expiration_date': ['date', 'date__gte', 'date__lte'],
    }
    
    search_fields = ['product__name', 'product__sku', 'batch_number']
    ordering_fields = ['expiration_date', 'manufacture_date', 'quantity']
    ordering = ['expiration_date']
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get products expiring within specified days (default 7)"""
        days = int(request.query_params.get('days', 7))
        cutoff_date = timezone.now().date() + timedelta(days=days)
        
        expiring_products = self.get_queryset().filter(
            expiration_date__lte=cutoff_date,
            expiration_date__gte=timezone.now().date(),
            is_expired=False
        ).select_related('product')
        
        serializer = self.get_serializer(expiring_products, many=True)
        return Response({
            'days_threshold': days,
            'count': expiring_products.count(),
            'products': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def expired_products(self, request):
        """Get all expired products"""
        expired_products = self.get_queryset().filter(
            Q(expiration_date__lt=timezone.now().date()) | Q(is_expired=True)
        ).select_related('product')
        
        serializer = self.get_serializer(expired_products, many=True)
        return Response({
            'count': expired_products.count(),
            'products': serializer.data
        })


class BarcodeCheckView(APIView):

    def post(self, request):
        serializer = BarcodeCheckSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"is_unique": True}, status=status.HTTP_200_OK)
        return Response({"is_unique": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    

class ProductImageViewSet(viewsets.ModelViewSet): # Create ProductImageViewSet

    serializer_class = ProductImageSerializer
    permission_classes = [IsInventoryStaffOrReadOnly] # Adjust permission as needed
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at'] # Default ordering

    def get_queryset(self): # Filter queryset to product images of a specific product
        product_pk = self.kwargs.get('product_pk') # Get product_pk from URL kwargs
        if product_pk:
            return ProductImage.objects.filter(product_id=product_pk) # Filter by product_id
        return ProductImage.objects.none() # Return empty queryset if no product_pk

    def perform_create(self, serializer): # Automatically associate product with image on creation
        product_pk = self.kwargs.get('product_pk') # Get product_pk from URL
        product = Product.objects.get(pk=product_pk) # Get Product instance
        serializer.save(product=product) # Save ProductImage with associated product

    @action(detail=False, methods=['post']) # Custom action for bulk create/update/delete
    def bulk_manage(self, request, product_pk=None): # bulk_manage action
        product = Product.objects.get(pk=product_pk) # Get Product Instance
        image_data_list = request.data # Expecting list of image data in request.data
        created_images = []
        updated_images = []
        deleted_image_ids = []

        for image_data in image_data_list: # Iterate through the list of image data
            action_type = image_data.get('action') # Get action type from data ('create', 'update', 'delete')
            image_id = image_data.get('id') # Get image ID if action is 'update' or 'delete'
            image_base64_string = image_data.get('image', None)
            if image_base64_string:
                try:
                    if ';base64,' in image_base64_string:
                        format, imgstr = image_base64_string.split(';base64,')
                    else:
                        imgstr = image_base64_string  # Handle case where there's no format prefix
                    image_data_decoded = base64.b64decode(imgstr)
                    image_file = ContentFile(image_data_decoded, name=f'{product.sku}-{len(product.images.all()) + 1}.png')
                except Exception as e:
                    return Response({"error": f"Error decoding image data: {e}"}, status=status.HTTP_400_BAD_REQUEST)

            if action_type == 'create': # Handle create action
                serializer = ProductImageSerializer(data={
                    'product': product_pk,
                    'image': image_file,
                    'is_thumbnail': image_data.get('is_thumbnail', False),
                }) # Use ProductImageSerializer
                if serializer.is_valid():
                    image_instance = serializer.save(product=product) # Create and associate with product
                    created_images.append(ProductImageSerializer(image_instance).data) # Append serialized created image
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) # Return error if invalid

            elif action_type == 'update' and image_id: # Handle update action
                try:
                    image_instance = ProductImage.objects.get(pk=image_id, product=product) # Get existing ProductImage
                    serializer = ProductImageSerializer(image_instance, data={
                        'is_thumbnail': image_data.get('is_thumbnail', False)
                    }, partial=True) # Partial update
                    if serializer.is_valid():
                        serializer.save() # Save updated instance
                        updated_images.append(serializer.data) # Append serialized updated image
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) # Return error if invalid
                except ProductImage.DoesNotExist:
                    return Response({'detail': f'Image with id {image_id} not found for this product.'}, status=status.HTTP_404_NOT_FOUND) # Image not found

            elif action_type == 'delete' and image_id: # Handle delete action
                deleted_image_ids.append(image_id) # Add image ID to deleted list
                try:
                    image_instance = ProductImage.objects.get(pk=image_id, product=product) # Get image to delete
                    image_instance.delete() # Delete image instance
                except ProductImage.DoesNotExist:
                    print(f"Warning: Image with id {image_id} not found for deletion.") # Log warning if not found

        response_data = { # Prepare response data
            'created': created_images,
            'updated': updated_images,
            'deleted_ids': deleted_image_ids,
            'message': 'Bulk image management completed.',
        }
        return Response(response_data, status=status.HTTP_200_OK) # Return success response



class ProductVariantViewSet(viewsets.ModelViewSet): # Create ProductVariantViewSet

    serializer_class = ProductVariantSerializer
    permission_classes = [IsInventoryStaffOrReadOnly] # Adjust permission as needed
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['name', 'value', 'additional_price', 'stock_quantity', 'created_at', 'updated_at']
    ordering = ['name', 'value'] # Default ordering by name and value

    def get_queryset(self): # Filter queryset to product variants of a specific product
        product_pk = self.kwargs.get('product_pk') # Get product_pk from URL kwargs
        if product_pk:
            return ProductVariant.objects.filter(product_id=product_pk) # Filter by product_id
        return ProductVariant.objects.none() # Return empty queryset if no product_pk

    def perform_create(self, serializer): # Automatically associate product with variant on creation
        product_pk = self.kwargs.get('product_pk') # Get product_pk from URL
        product = Product.objects.get(pk=product_pk) # Get Product instance
        serializer.save(product=product) # Save ProductVariant with associated product

    @action(detail=False, methods=['post']) # Custom action for bulk create/update/delete variants
    def bulk_manage(self, request, product_pk=None): # bulk_manage action for variants
        product = Product.objects.get(pk=product_pk) # Get Product Instance
        variant_data_list = request.data # Expecting list of variant data in request.data
        created_variants = []
        updated_variants = []
        deleted_variant_ids = []

        for variant_data in variant_data_list: # Iterate through the list of variant data
            action_type = variant_data.get('action') # Get action type from data ('create', 'update', 'delete')
            variant_id = variant_data.get('id') # Get variant ID if action is 'update' or 'delete'

            if action_type == 'create': # Handle create action
                serializer = ProductVariantSerializer(data={
                    'product': product_pk,
                    **variant_data
                }) # Use ProductVariantSerializer
                if serializer.is_valid():
                    variant_instance = serializer.save(product=product) # Create and associate with product
                    created_variants.append(ProductVariantSerializer(variant_instance).data) # Append serialized created variant
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) # Return error if invalid

            elif action_type == 'update' and variant_id: # Handle update action
                try:
                    variant_instance = ProductVariant.objects.get(pk=variant_id, product=product) # Get existing ProductVariant
                    serializer = ProductVariantSerializer(variant_instance, data=variant_data, partial=True) # Partial update
                    if serializer.is_valid():
                        serializer.save() # Save updated instance
                        updated_variants.append(serializer.data) # Append serialized updated variant
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) # Return error if invalid
                except ProductVariant.DoesNotExist:
                    return Response({'detail': f'Variant with id {variant_id} not found for this product.'}, status=status.HTTP_404_NOT_FOUND) # Variant not found

            elif action_type == 'delete' and variant_id: # Handle delete action
                deleted_variant_ids.append(variant_id) # Add variant ID to deleted list
                try:
                    variant_instance = ProductVariant.objects.get(pk=variant_id, product=product) # Get variant to delete
                    variant_instance.delete() # Delete variant instance
                except ProductVariant.DoesNotExist:
                    print(f"Warning: Variant with id {variant_id} not found for deletion.") # Log warning if not found

        response_data = { # Prepare response data
            'created': created_variants,
            'updated': updated_variants,
            'deleted_ids': deleted_variant_ids,
            'message': 'Bulk variant management completed.',
        }
        return Response(response_data, status=status.HTTP_200_OK) # Return success response