
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(["GET"])
def controller_config(request):
    # Демоверсия: ключи-заглушки и политика
    return Response({
        "keys":[
            {"kid":"key-2025-09-A","pub_pem":"-----BEGIN PUBLIC KEY-----\n...demo...\n-----END PUBLIC KEY-----","not_after":1700000000,"revoked":False}
        ],
        "policy":{"max_apdu_ms":200,"session_ttl":60}
    })
