import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from app.api.controllers import IndexView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('app.api.urls')),
    
    # Route for compiled React frontend assets (/assets/*)
    re_path(
        r'^assets/(?P<path>.*)$', 
        serve, 
        {'document_root': os.path.join(settings.BASE_DIR.parent, 'frontend', 'dist', 'assets')}
    ),
    
    # Route for favicon
    re_path(
        r'^favicon\.svg$', 
        serve, 
        {
            'document_root': os.path.join(settings.BASE_DIR.parent, 'frontend', 'dist'),
            'path': 'favicon.svg'
        }
    ),
    
    # Catch-all template view for client-side React Router matching (ignores API, admin, and assets)
    re_path(r'^(?!api/|admin/|assets/).*$', IndexView.as_view(), name='index'),
]
