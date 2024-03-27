from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView

from .views import (NetworkListView, NetworkCreateView, NetworkUpdateView, NetworkDeleteView, 
                    ChargerListView, ChargerCreateView, ChargerUpdateView, ChargerDeleteView,
                    UserListView, UserCreateView, UserUpdateView, UserDeleteView,
                    View_Charger_Transactions)

urlpatterns = [
    
    re_path(r'^$', RedirectView.as_view(url='/networks/', permanent=False), name='index'),

    # Network URLs
    path('networks/', NetworkListView.as_view(), name='network-list'),
    path('networks/create/', NetworkCreateView.as_view(), name='network-create'),
    path('networks/update/<int:pk>/', NetworkUpdateView.as_view(), name='network-update'),
    path('networks/delete/<int:pk>/', NetworkDeleteView.as_view(), name='network-delete'),
    
    # Charger URLs
    path('chargers/', ChargerListView.as_view(), name='charger-list'),
    path('chargers/create/', ChargerCreateView.as_view(), name='charger-create'),
    path('chargers/update/<int:pk>/', ChargerUpdateView.as_view(), name='charger-update'),
    path('chargers/delete/<int:pk>/', ChargerDeleteView.as_view(), name='charger-delete'),

    #User URLs
    
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/create/', UserCreateView.as_view(), name='user-create'),
    path('users/update/<int:pk>/', UserUpdateView.as_view(), name='user-update'),
    path('users/delete/<int:pk>/', UserDeleteView.as_view(), name='user-delete'),

    # Transaction URLs
    path('chargers/<str:charger_id>/transactions/', View_Charger_Transactions, name='view_charger_transactions'),

]