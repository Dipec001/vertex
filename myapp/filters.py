from django_filters import rest_framework as filters

from myapp.models import CustomUser, Company


class EmployeeFilterSet(filters.FilterSet):
    company = filters.CharFilter(field_name="company__name",lookup_expr="icontains")
    company_id = filters.CharFilter(field_name="company")
    date_joined = filters.DateFilter(field_name="date_joined", lookup_expr="date")

    class Meta:
        model = CustomUser
        fields = ['company', 'company_id', 'is_active','is_company_owner', 'login_type', 'date_joined']

class CompanyFilterSet(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    class Meta:
        model = Company
        fields = ['name']
