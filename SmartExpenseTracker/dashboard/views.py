from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from transactions.models import Expense
from django.db.models import Sum


@login_required
def dashboard_view(request):
    user = request.user

    # Calculate totals
    income_total = Expense.objects.filter(
        user=user, transaction_type__iexact="income"
    ).aggregate(total=Sum("amount"))["total"] or 0

    expense_total = Expense.objects.filter(
        user=user, transaction_type__iexact="expense"
    ).aggregate(total=Sum("amount"))["total"] or 0

    balance = income_total - expense_total

    # Recent 5 transactions
    recent_transactions = Expense.objects.filter(user=user).order_by("-date", "-created_at")[:5]

    context = {
        "income_total": income_total,
        "expense_total": expense_total,
        "balance": balance,
        "recent_transactions": recent_transactions,
    }
    return render(request, "dashboard/dashboard.html", context)