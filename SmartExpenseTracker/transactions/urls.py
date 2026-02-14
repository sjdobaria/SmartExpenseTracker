from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('add-transaction/', views.add_transaction_view,name='add_transaction_view'),
    path('transactions_history/', views.transactions_view,name='transactions_view'),
    
]
