
from rest_framework import serializers

class VerifyApduSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    exp = serializers.IntegerField()
    payload_b64 = serializers.CharField()
    sig_b64 = serializers.CharField()
    kid = serializers.CharField(required=False)

class VerifyRequestSerializer(serializers.Serializer):
    door_id = serializers.CharField()
    ts = serializers.IntegerField()
    apdu = VerifyApduSerializer()
    controller_info = serializers.DictField()

class EventItemSerializer(serializers.Serializer):
    door_id = serializers.CharField()
    ts = serializers.IntegerField()
    decision = serializers.CharField()
    user_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    token_hash_prefix = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    reason = serializers.CharField()

class EventBatchSerializer(serializers.Serializer):
    controller_id = serializers.CharField()
    batch = EventItemSerializer(many=True)
