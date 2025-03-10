from django.urls import path, include
from .views import UserRegistrationView, UserProfileView, UserViewSet # Import UserViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter # Import DefaultRouter
from .throttling import LoginRateThrottle

router = DefaultRouter() # Create a router
router.register(r'users', UserViewSet, basename='user-admin') # Register UserViewSet for admin user management

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', TokenObtainPairView.as_view(throttle_classes=[LoginRateThrottle]), name='user-login'), # JWT login (get access and refresh tokens)
    path('login/refresh/', TokenRefreshView.as_view(), name='token-refresh'), # Refresh access token
    path('profile/', UserProfileView.as_view(), name='user-profile'), # Get/Update logged-in user's profile
    path('', include(router.urls)), # Include router URLs for UserViewSet - placed at the end to avoid conflict with 'profile/' path
]