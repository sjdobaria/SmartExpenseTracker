from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('add-transaction/', views.add_expense, name='add_transaction'),
    path('transactions_history/', views.transactions_view, name='transactions'),
    path('edit/<int:pk>/', views.edit_expense, name='edit_transaction'),
    path('delete/<int:pk>/', views.delete_expense, name='delete_transaction'),
    path('categories/', views.categories_view, name='categories'),
    path('categories/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete_category'),
    path('reports/', views.reports_view, name='reports'),
]
