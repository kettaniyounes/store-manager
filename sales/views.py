# Django Import
from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from .models import PaymentMethod, SaleTransaction
from .serializers import PaymentMethodSerializer, SaleTransactionSerializer
from .permissions import IsManagerOrReadOnly, IsSalesStaffOrReadOnly, IsManagerOrOwnerSale


# Python Import


class PaymentMethodViewSet(viewsets.ModelViewSet):

    queryset = PaymentMethod.objects.filter(is_active=True).order_by('name') # Filter active payment methods, order by name
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsManagerOrReadOnly] # Use IsManagerOrReadOnly permission
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] # Add filter backends
    search_fields = ['name', 'description'] # Fields for search
    ordering_fields = ['name', 'created_at'] # Fields for ordering
    ordering = ['name'] # Default ordering


class SaleTransactionViewSet(viewsets.ModelViewSet):

    queryset = SaleTransaction.objects.all().order_by('-sale_date') # Order by sale date descending
    serializer_class = SaleTransactionSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Default permission - refine
    permission_classes = [IsSalesStaffOrReadOnly] # Use IsSalesStaffOrReadOnly permission
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] # Filter backends
    filterset_fields = ['sale_date', 'payment_method', 'customer', 'salesperson'] # Filter fields
    search_fields = ['transaction_id', 'customer__name', 'salesperson__username'] # Search fields (related fields)
    ordering_fields = ['sale_date', 'total_amount', 'created_at'] # Ordering fields
    ordering = ['-sale_date'] # Default ordering

    def get_permissions(self):
        # Use more restrictive permission for DELETE action
        if self.action == 'destroy':
            return [IsManagerOrOwnerSale()]
        return super().get_permissions()

    def perform_create(self, serializer):
        # Example: Automatically set salesperson to current user if not provided
        if not serializer.validated_data.get('salesperson'):
            serializer.save(salesperson=self.request.user)
        else:
            serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer) # Call perform_create to save and potentially add extra logic
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs): # Example of customizing DELETE action (voiding instead of deleting)

        '''
        Instead of deleting, consider voiding the transaction (set status to 'voided' if you add a status field)
        instance.status = 'voided'
        instance.save()
        serializer = self.get_serializer(instance) # Serialize the updated instance
        return Response(serializer.data, status=status.HTTP_200_OK) # Return updated instance instead of 204
        '''

        instance = self.get_object()

        with transaction.atomic():
            instance.status = 'voided'
            instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)