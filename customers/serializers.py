
# Django Import
from rest_framework import serializers
from .models import Customer

# Python Import



class CustomerSerializer(serializers.ModelSerializer):
    
    name = serializers.CharField(max_length=255, required=True) # Make 'name' explicitly required
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True) # 'phone_number' optional, allow blank
    email = serializers.EmailField(required=False, allow_blank=True) # 'email' optional, allow blank, EmailField for validation
    address = serializers.CharField(required=False, allow_blank=True) # 'address' optional, allow blank
    notes = serializers.CharField(required=False, allow_blank=True) # 'notes' optional, allow blank
    
    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone_number', 'email', 'address', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    