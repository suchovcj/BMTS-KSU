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
    path('reports/', views.reports, name='reports'),
    path('map/', views.map, name='map'),
    path('create-ticket/', views.create_ticket, name='create_ticket'),
    path('staff/', views.staff_list, name='staff'),  # Staff management URL
    path('staff/add/', views.add_staff, name='add_staff'),  # For adding new staff
    path('staff/edit/<int:staff_id>/', views.edit_staff, name='edit_staff'),
    path('staff/delete/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('facilities/', views.facilities, name='facilities'),
    path('qr-codes/', views.qr_codes, name='qr_codes'),
    path('print-qr-codes/', views.print_qr_codes, name='print_qr_codes')
]