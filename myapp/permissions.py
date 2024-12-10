import logging

from django.http import Http404
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404

from myapp.models import Company

# Set up logging
logger = logging.getLogger(__name__)

class IsCompanyOwner(permissions.BasePermission):
    """
    Custom permission to only allow company owners to access the view.
    
    Requires:
        - URL path must contain a 'company_id' parameter
        - User must be authenticated
        - User must be the owner of the company specified by company_id
    
    Example URL pattern:
        path('companies/<int:company_id>/employees/', EmployeeByCompanyModelView.as_view(), name='employee-by-company')
    
    Raises:
        ValueError: If company_id is not provided in the URL path
        PermissionDenied: If the user is not the owner of the specified company
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Get company_id from URL parameters
        company_id = view.kwargs.get('company_id')
        if not company_id:
            logger.error("Company ID is missing in the URL path.")
            raise ValueError("Company ID is required in the URL path.")

        # Check if the company exists
        get_object_or_404(Company, id=company_id)
        if not request.user.owned_company.filter(id=company_id).exists():
            return False
        
        return True