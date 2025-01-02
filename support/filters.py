from django_filters import rest_framework as filters

from .models import Ticket


class TicketFilterSet(filters.FilterSet):
    title = filters.CharFilter(lookup_expr="icontains")
    company = filters.CharFilter(field_name="company__name", lookup_expr="icontains")
    created_by = filters.CharFilter(field_name="created_by__username", lookup_expr="icontains")
    is_individual = filters.BooleanFilter()
    class Meta:
        model = Ticket
        fields = ['title', 'status', 'created_by', 'company', 'is_individual']
