from django.shortcuts import render

# Create your views here.
def add_transaction_view(request):
    return render(request,'transactions/add-transaction.html')
def transactions_view(request):
    return render(request,'transactions/transactions.html')