from django_filters import rest_framework as filters

from myapp.models import CustomUser


class EmployeeFilterSet(filters.FilterSet):
    email = filters.CharFilter(lookup_expr="icontains")
    username = filters.CharFilter(lookup_expr="icontains")
    company = filters.CharFilter(field_name="company__name",lookup_expr="icontains")
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'company']