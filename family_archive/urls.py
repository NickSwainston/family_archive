"""family_archive URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
import re

from django.urls import path, include, re_path
from django.conf import settings

from archive_app import views

urlpatterns = [
    path('', views.home_page, name='home_page'),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('family_tree/', views.family_tree),
    path('gallery/', views.gallery),
    path('tag_images/', views.tag_images_form, name='tag_images'),
    path('update_image/<int:image_id>/', views.update_image, name='update_image'),
    path('post_create/', views.PostCreateView.as_view(), name='post_create'),
    path('timeline/', views.timeline, name='timeline'),
    path('events/new/', views.event_create, name='event_create'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/edit/', views.event_edit, name='event_edit'),
]

# Serve uploaded media (photos/videos) from MEDIA_ROOT. The static() helper only works when DEBUG=True,
# so register the view directly; there's no separate web server for /media/ in the k8s deployment.
urlpatterns += [
    re_path(r'^%s(?P<path>.*)$' % re.escape(settings.MEDIA_URL.lstrip('/')), views.serve_media),
]