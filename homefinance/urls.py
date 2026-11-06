"""A projekt szintű URL-konfiguráció."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("finance.urls")),
]

admin.site.site_header = "HomeFinance adminisztráció"
admin.site.site_title = "HomeFinance"
admin.site.index_title = "Adminisztráció"
