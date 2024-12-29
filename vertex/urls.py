"""
URL configuration for vertex project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from django.conf import settings 
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("myapp.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("missions.urls")),
    path("api/", include("supportticket.urls")),
    path('auth/', include('rest_framework.urls')),  # DRF browsable API login/logout
    path('social-auth/', include('allauth.urls')), # For social login (Google, Facebook, etc.) 
    path('api/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Only allow creation of devices by authenticated users
    path('api/devices/', FCMDeviceAuthorizedViewSet.as_view({'post': 'create'}), name='create_fcm_device'),

]