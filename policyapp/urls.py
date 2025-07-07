from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("policies/", views.policy_list, name="list_policies"),
    path("policies/<int:pk>/", views.view_policy, name="view_policy"),
    path("delete/<int:pk>/", views.delete_policy, name="delete_policy"),
]
