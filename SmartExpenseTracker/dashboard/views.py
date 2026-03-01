import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from transactions.models import Expense
from django.db.models import Sum
from django.db.models.functions import TruncMonth


@login_required
def dashboard_view(request):
    user = request.user

    # ── Summary totals ──
    income_total = Expense.objects.filter(
        user=user, transaction_type__iexact="income"
    ).aggregate(total=Sum("amount"))["total"] or 0

    expense_total = Expense.objects.filter(
        user=user, transaction_type__iexact="expense"
    ).aggregate(total=Sum("amount"))["total"] or 0

    balance = income_total - expense_total

    # ── Recent 5 transactions ──
    recent_transactions = Expense.objects.filter(user=user).order_by("-date", "-created_at")[:5]

    # ── Pie chart: Expense by category ──
    category_data = (
        Expense.objects.filter(user=user, transaction_type__iexact="expense")
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    pie_labels = [item["category"] for item in category_data]
    pie_values = [float(item["total"]) for item in category_data]

    # ── Line chart: Monthly income vs expense (last 6 months) ──
    monthly_income = (
        Expense.objects.filter(user=user, transaction_type__iexact="income")
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )
    monthly_expense = (
        Expense.objects.filter(user=user, transaction_type__iexact="expense")
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    # Build a merged set of months
    all_months: set = set()
    income_map: dict = {}
    expense_map: dict = {}

    for item in monthly_income:
        month_str = item["month"].strftime("%b %Y")
        income_map[month_str] = float(item["total"])
        all_months.add(item["month"])

    for item in monthly_expense:
        month_str = item["month"].strftime("%b %Y")
        expense_map[month_str] = float(item["total"])
        all_months.add(item["month"])

    sorted_all = sorted(all_months)
    sorted_months = sorted_all[-6:] if len(sorted_all) > 6 else sorted_all  # last 6 months
    line_labels = [m.strftime("%b %Y") for m in sorted_months]
    line_income = [income_map.get(label, 0) for label in line_labels]
    line_expense = [expense_map.get(label, 0) for label in line_labels]

    context = {
        "active_page": "dashboard",
        "income_total": income_total,
        "expense_total": expense_total,
        "balance": balance,
        "recent_transactions": recent_transactions,
        # Chart data as JSON
        "pie_labels": json.dumps(pie_labels),
        "pie_values": json.dumps(pie_values),
        "line_labels": json.dumps(line_labels),
        "line_income": json.dumps(line_income),
        "line_expense": json.dumps(line_expense),
    }
    return render(request, "dashboard/dashboard.html", context)