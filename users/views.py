
# Django Import
from rest_framework import generics, permissions, status, viewsets
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import filters
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from .serializers import UserRegistrationSerializer, UserSerializer, UserProfileSerializer
from .permissions import IsAdminOrReadOnlyUser

# Python Import


class UserRegistrationView(generics.CreateAPIView):
    
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny] # Allow anyone to register

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        response_data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    
    serializer_class = UserProfileSerializer # Use UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated] # Only authenticated users can view/update their profile
    authentication_classes = [JWTAuthentication]

    def get_object(self):
        return self.request.user.profile


class UserViewSet(viewsets.ModelViewSet): # User management ViewSet (Admin only)

    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrReadOnlyUser] # Restrict to admin users (you'll create this permission)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter] # Add filters
    search_fields = ['username', 'email', 'first_name', 'last_name'] # Search fields
    ordering_fields = ['username', 'date_joined', 'last_login'] # Ordering fields
    ordering = ['username'] # Default ordering

    def perform_create(self, serializer): # Example: Auto-set is_staff=True for new users created via admin API
        serializer.save(is_staff=True) # Or based on some logic/role

    def perform_update(self, serializer): # Example: Prevent non-admin users from changing is_superuser
        if not self.request.user.is_superuser and 'is_superuser' in serializer.validated_data:
            serializer.validated_data.pop('is_superuser') # Remove is_superuser from validated data if current user is not superuser
        serializer.save()