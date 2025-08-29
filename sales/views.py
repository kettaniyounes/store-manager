# Django Import
from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    PaymentMethod, SaleTransaction, FinancialPeriod, ProfitLossReport,
    SalesAnalytics, TaxReport
)
from .serializers import (
    PaymentMethodSerializer, SaleTransactionSerializer, FinancialPeriodSerializer,
    ProfitLossReportSerializer, SalesAnalyticsSerializer, TaxReportSerializer,
    DailySalesReportSerializer, MonthlySalesReportSerializer, TopProductsReportSerializer,
    SalespersonPerformanceSerializer
)
from .permissions import IsManagerOrReadOnly, IsSalesStaffOrReadOnly, IsManagerOrOwnerSale
from products.models import Product

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
    filterset_fields = ['sale_date', 'payment_method', 'customer', 'salesperson', 'status'] # Filter fields
    search_fields = ['transaction_id', 'customer__name', 'salesperson__username'] # Search fields (related fields)
    ordering_fields = ['sale_date', 'total_amount', 'gross_profit', 'created_at'] # Ordering fields
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

    @action(detail=False, methods=['get'])
    def daily_sales_summary(self, request):
        """Get daily sales summary for a date range"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date:
            start_date = timezone.now().date()
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if not end_date:
            end_date = start_date
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Query sales data grouped by date
        daily_sales = SaleTransaction.objects.filter(
            sale_date__date__range=[start_date, end_date],
            status='completed'
        ).extra(
            select={'date': 'DATE(sale_date)'}
        ).values('date').annotate(
            total_revenue=Sum('total_amount'),
            total_transactions=Count('id'),
            total_items_sold=Sum('sale_items__quantity'),
            average_transaction_value=Avg('total_amount'),
            total_profit=Sum('gross_profit'),
        ).order_by('date')
        
        # Calculate profit margin for each day
        for day in daily_sales:
            if day['total_revenue'] and day['total_revenue'] > 0:
                day['profit_margin'] = (day['total_profit'] / day['total_revenue']) * 100
            else:
                day['profit_margin'] = 0
        
        serializer = DailySalesReportSerializer(daily_sales, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def monthly_sales_summary(self, request):
        """Get monthly sales summary"""
        year = int(request.query_params.get('year', timezone.now().year))
        
        monthly_sales = SaleTransaction.objects.filter(
            sale_date__year=year,
            status='completed'
        ).extra(
            select={
                'month': 'EXTRACT(month FROM sale_date)',
                'year': 'EXTRACT(year FROM sale_date)'
            }
        ).values('month', 'year').annotate(
            total_revenue=Sum('total_amount'),
            total_transactions=Count('id'),
            total_customers=Count('customer', distinct=True),
            average_transaction_value=Avg('total_amount'),
            total_profit=Sum('gross_profit'),
        ).order_by('month')
        
        # Calculate profit margin and growth percentage
        previous_revenue = 0
        for month_data in monthly_sales:
            if month_data['total_revenue'] and month_data['total_revenue'] > 0:
                month_data['profit_margin'] = (month_data['total_profit'] / month_data['total_revenue']) * 100
            else:
                month_data['profit_margin'] = 0
            
            # Calculate growth percentage
            if previous_revenue > 0:
                month_data['growth_percentage'] = ((month_data['total_revenue'] - previous_revenue) / previous_revenue) * 100
            else:
                month_data['growth_percentage'] = 0
            
            previous_revenue = month_data['total_revenue']
            
            # Convert month number to name
            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            month_data['month'] = month_names[int(month_data['month'])]
        
        serializer = MonthlySalesReportSerializer(monthly_sales, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_products_report(self, request):
        """Get top selling products report"""
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))
        start_date = timezone.now().date() - timedelta(days=days)
        
        top_products = SaleTransaction.objects.filter(
            sale_date__date__gte=start_date,
            status='completed'
        ).values(
            'sale_items__product__id',
            'sale_items__product__name',
            'sale_items__product__sku',
            'sale_items__product__category__name'
        ).annotate(
            product_id=F('sale_items__product__id'),
            product_name=F('sale_items__product__name'),
            product_sku=F('sale_items__product__sku'),
            category_name=F('sale_items__product__category__name'),
            total_quantity_sold=Sum('sale_items__quantity'),
            total_revenue=Sum('sale_items__line_total'),
            total_profit=Sum('sale_items__gross_profit'),
        ).order_by('-total_quantity_sold')[:limit]
        
        # Calculate profit margin for each product
        for product in top_products:
            if product['total_revenue'] and product['total_revenue'] > 0:
                product['profit_margin'] = (product['total_profit'] / product['total_revenue']) * 100
            else:
                product['profit_margin'] = 0
        
        serializer = TopProductsReportSerializer(top_products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def salesperson_performance(self, request):
        """Get salesperson performance report"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        performance = SaleTransaction.objects.filter(
            sale_date__date__gte=start_date,
            status='completed',
            salesperson__isnull=False
        ).values(
            'salesperson__id',
            'salesperson__username'
        ).annotate(
            salesperson_id=F('salesperson__id'),
            salesperson_name=F('salesperson__username'),
            total_sales=Sum('total_amount'),
            total_transactions=Count('id'),
            average_transaction_value=Avg('total_amount'),
            total_profit_generated=Sum('gross_profit'),
        ).order_by('-total_sales')
        
        serializer = SalespersonPerformanceSerializer(performance, many=True)
        return Response(serializer.data)


class FinancialPeriodViewSet(viewsets.ModelViewSet):
    """ViewSet for managing financial periods"""
    
    queryset = FinancialPeriod.objects.all().order_by('-start_date')
    serializer_class = FinancialPeriodSerializer
    permission_classes = [IsManagerOrReadOnly]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['period_type', 'is_closed']
    search_fields = ['name']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-start_date']


class ProfitLossReportViewSet(viewsets.ModelViewSet):
    """ViewSet for Profit & Loss reports"""
    
    queryset = ProfitLossReport.objects.all().order_by('-generated_at')
    serializer_class = ProfitLossReportSerializer
    permission_classes = [IsManagerOrReadOnly]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['period', 'period__period_type']
    ordering_fields = ['generated_at', 'total_revenue', 'net_profit']
    ordering = ['-generated_at']
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate P&L report for the period"""
        report = self.get_object()
        report.calculate_metrics()
        serializer = self.get_serializer(report)
        return Response(serializer.data)


class SalesAnalyticsViewSet(viewsets.ModelViewSet):
    """ViewSet for sales analytics"""
    
    queryset = SalesAnalytics.objects.all().order_by('-generated_at')
    serializer_class = SalesAnalyticsSerializer
    permission_classes = [IsManagerOrReadOnly]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['period', 'period__period_type']
    ordering_fields = ['generated_at', 'total_sales_volume', 'unique_customers']
    ordering = ['-generated_at']


class TaxReportViewSet(viewsets.ModelViewSet):
    """ViewSet for tax reports"""
    
    queryset = TaxReport.objects.all().order_by('-generated_at')
    serializer_class = TaxReportSerializer
    permission_classes = [IsManagerOrReadOnly]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['period', 'period__period_type']
    ordering_fields = ['generated_at', 'total_tax_collected', 'total_taxable_sales']
    ordering = ['-generated_at']