from django import forms
from django.core.exceptions import ValidationError

from .models import HostIP

HOST_ORDER_FIELDS = (
    "id",
    "hostname",
    "ip_address",
    "description",
    "is_active",
    "created_at",
    "updated_at",
    "id",
)
MAX_PAGE_LENGTH = 100


class StrictBooleanField(forms.Field):
    """Accept JSON booleans without coercing other values to True or False."""

    default_error_messages = {"invalid": "Enter a valid boolean."}

    def to_python(self, value):
        if isinstance(value, bool):
            return value
        raise ValidationError(self.error_messages["invalid"], code="invalid")


class HostIPForm(forms.ModelForm):
    is_active = StrictBooleanField()

    class Meta:
        model = HostIP
        fields = ("hostname", "ip_address", "description", "is_active")


class HostIPDataTableForm(forms.Form):
    draw = forms.IntegerField(min_value=0)
    start = forms.IntegerField(min_value=0)
    length = forms.IntegerField(min_value=1, max_value=MAX_PAGE_LENGTH)
    order_column = forms.IntegerField(
        min_value=0,
        max_value=len(HOST_ORDER_FIELDS) - 1,
    )
    order_direction = forms.ChoiceField(
        choices=(("asc", "Ascending"), ("desc", "Descending"))
    )
