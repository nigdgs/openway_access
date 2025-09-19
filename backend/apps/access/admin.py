from django.contrib import admin
from .models import AccessPoint, AccessPermission, AccessEvent

@admin.register(AccessPoint)
class AccessPointAdmin(admin.ModelAdmin):
    list_display = ("code","name","location")
    search_fields = ("code","name","location")

@admin.register(AccessPermission)
class AccessPermissionAdmin(admin.ModelAdmin):
    list_display = ("access_point","user","group","allow")
    list_filter = ("allow","access_point")
    search_fields = ("user__username","group__name","access_point__code")

@admin.register(AccessEvent)
class AccessEventAdmin(admin.ModelAdmin):
    list_display = ("created_at","access_point","user","device_id","decision","reason")
    list_filter = ("decision","reason","access_point")
    search_fields = ("user__username","access_point__code","reason")
    readonly_fields = ("created_at","raw")