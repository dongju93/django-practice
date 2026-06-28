from django.db import models


class HostIP(models.Model):
    hostname = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(protocol="both", unpack_ipv4=False)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Host IP"
        verbose_name_plural = "Host IPs"

    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"
