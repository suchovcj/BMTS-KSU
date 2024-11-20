from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'bmts'
urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('open-tickets/', views.open_tickets, name='open_tickets'),
    path('closed-tickets/', views.closed_tickets, name='closed_tickets'),
    path('staff/', views.staff, name='staff'),
    path('reports/', views.reports, name='reports'),
    path('map/', views.map, name='map'),
    path('create-ticket/', views.create_ticket, name='create_ticket'),
]