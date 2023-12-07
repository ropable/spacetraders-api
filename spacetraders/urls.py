from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

admin.site.site_header = "SpaceTraders database administration"
admin.site.index_title = "SpaceTraders database"
admin.site.site_title = "SpaceTraders"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("favicon.ico", RedirectView.as_view(url="{}favicon.png".format(settings.STATIC_URL)), name="favicon"),
    path("", RedirectView.as_view(url="/admin")),
]
