from django.contrib import admin

from .models import HostIP


@admin.register(HostIP)
class HostIPAdmin(admin.ModelAdmin):
    list_display = ("hostname", "ip_address", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("hostname", "ip_address")
