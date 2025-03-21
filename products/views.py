
# Django Import
from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.core.files.base import ContentFile
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Category, Brand, Product, ProductImage, ProductVariant
from .serializers import CategorySerializer, BrandSerializer, ProductImageSerializer, ProductSerializer, BarcodeCheckSerializer, ProductVariantSerializer
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
    

class ProductImageViewSet(viewsets.ModelViewSet): # <---- Create ProductImageViewSet

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



class ProductVariantViewSet(viewsets.ModelViewSet): # <---- Create ProductVariantViewSet

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