
# Django Import
from rest_framework import serializers
from .models import StoreSetting


# Python Import


class StoreSettingSerializer(serializers.ModelSerializer):

    key = serializers.ChoiceField(choices=StoreSetting.KEY_CHOICES, required=True)
    value = serializers.CharField(required=True) # 'value' required
    data_type = serializers.ChoiceField(choices=StoreSetting.DATA_TYPE_CHOICES, required=True) # 'data_type' required, use ChoiceField
    description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = StoreSetting
        fields = ['id', 'key', 'value', 'data_type', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'key', 'data_type'] # key and data_type are read-only after creation


    