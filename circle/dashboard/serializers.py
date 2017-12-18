from rest_framework import serializers
from django.contrib.auth.models import User


class UserSerializer(serializers.HyperlinkedModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('url', 'full_name', 'email')

    def get_full_name(self, obj):
        return obj.get_full_name()
