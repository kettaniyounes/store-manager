
# Django Import
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile

# Python Import


class UserSerializer(serializers.ModelSerializer):

    role = serializers.CharField(source='profile.get_role_display', read_only=True) # Display user role

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active', 'date_joined', 'last_login')
        read_only_fields = ('id', 'date_joined', 'last_login', 'role') # role is read-only here, managed via


class UserRegistrationSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, required=True, min_length=8, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, min_length=8, style={'input_type': 'password'})
    email = serializers.EmailField(required=True, allow_blank=False) # Email required, not blank
    first_name = serializers.CharField(max_length=30, required=False, allow_blank=True) # 'first_name' optional
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True) # 'last_name' optional
    role = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name','role')
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8}, # Redundant min_length, but for clarity
            'password2': {'write_only': True, 'min_length': 8}, # Redundant min_length, but for clarity
            'username': {'min_length': 3, 'max_length': 150}, # Username min/max length
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return data

    def create(self, validated_data):
        role = validated_data.pop('role')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name') or '',  # Use empty string if not provided
            last_name=validated_data.get('last_name') or '',    # Use empty string if not provided
            password=validated_data['password']
        )
        # Create UserProfile automatically after user creation (optional, can also be done via signals)
        UserProfile.objects.create(user=user, role=role)
        return user



class UserProfileSerializer(serializers.ModelSerializer):
    
    username = serializers.CharField(source='user.username', read_only=True) # Display username from related User
    email = serializers.EmailField(source='user.email', read_only=True) # Display email from related User
    first_name = serializers.CharField(source='user.first_name', required=False) # Display first_name from related User
    last_name = serializers.CharField(source='user.last_name', required=False) # Display last_name from related User
    role = serializers.CharField(required=False) # Role is optional for profile updates (or make it required based on your logic)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'username', 'email', 'first_name', 'last_name', 'role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'username', 'email'] # user and user details are read-only here

    def update(self, instance, validated_data):
        # Pop user data from the validated_data.
        user_data = validated_data.pop('user', {})
        user = instance.user

        # Update the related user's first_name and last_name if provided.
        user.first_name = user_data.get('first_name', user.first_name)
        user.last_name = user_data.get('last_name', user.last_name)
        user.save()

        # Update the profile instance with any remaining validated_data.
        return super().update(instance, validated_data)