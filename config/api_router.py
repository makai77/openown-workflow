from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from openown.applications.views import ApplicationViewSet
from openown.applications.views import ReviewerApplicationViewSet
from openown.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("applications", ApplicationViewSet, basename="application")
router.register(
    "reviewer/applications",
    ReviewerApplicationViewSet,
    basename="reviewer-application",
)


app_name = "api"
urlpatterns = router.urls
