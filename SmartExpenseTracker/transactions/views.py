import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Expense, Category
from django.contrib import messages
from datetime import date, timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth, TruncDate
from .mongo import get_transactions_collection


# ──────────────────────────────────────────────────
#  ADD TRANSACTION
# ──────────────────────────────────────────────────
@login_required
def add_expense(request):
    if request.method == "POST":
        transaction_type = request.POST.get("type")
        amount = request.POST.get("amount")
        category = request.POST.get("category")
        description = request.POST.get("description")
        expense_date = request.POST.get("date")
        payment_mode = request.POST.get("payment")

        if not amount or not category or not expense_date:
            messages.error(request, "Please fill all required fields.")
            return redirect("transactions:add_transaction")

        try:
            amount_val = float(amount)
            if amount_val <= 0:
                messages.error(request, "Amount must be greater than 0.")
                return redirect("transactions:add_transaction")
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid amount.")
            return redirect("transactions:add_transaction")

        expense = Expense.objects.create(
            user=request.user,
            amount=amount,
            category=category,
            description=description,
            date=expense_date,
            transaction_type=transaction_type,
            payment_mode=payment_mode,
        )

        # Save to MongoDB as well
        collection = get_transactions_collection()
        collection.insert_one({
            "user_id": request.user.id,
            "username": request.user.username,
            "amount": float(amount),
            "category": category,
            "description": description,
            "date": expense_date,
            "transaction_type": transaction_type,
            "payment_mode": payment_mode,
            "created_at": expense.created_at.isoformat(),
        })

        messages.success(request, "Transaction added successfully!")
        return redirect("transactions:transactions")

    # GET – load dynamic categories
    income_categories = Category.objects.filter(user=request.user, type="income")
    expense_categories = Category.objects.filter(user=request.user, type="expense")
    context = {
        "income_categories": income_categories,
        "expense_categories": expense_categories,
    }
    return render(request, "transactions/add-transaction.html", context)


# ──────────────────────────────────────────────────
#  TRANSACTIONS LIST + FILTERS
# ──────────────────────────────────────────────────
@login_required
def transactions_view(request):
    user = request.user
    qs = Expense.objects.filter(user=user).order_by("-date", "-created_at")

    # --- Filters ---
    filter_category = request.GET.get("category", "")
    filter_type = request.GET.get("type", "")
    filter_month = request.GET.get("month", "")

    if filter_category:
        qs = qs.filter(category=filter_category)
    if filter_type:
        qs = qs.filter(transaction_type__iexact=filter_type)
    if filter_month:
        try:
            year, month = filter_month.split("-")
            qs = qs.filter(date__year=int(year), date__month=int(month))
        except ValueError:
            pass

    # Load user categories for the filter dropdown
    all_categories = Category.objects.filter(user=user).values_list("name", flat=True).distinct()

    context = {
        "transactions": qs,
        "filter_category": filter_category,
        "filter_type": filter_type,
        "filter_month": filter_month,
        "all_categories": all_categories,
    }
    return render(request, "transactions/transactions.html", context)


# ──────────────────────────────────────────────────
#  DELETE TRANSACTION
# ──────────────────────────────────────────────────
@login_required
def delete_expense(request, pk):
    try:
        expense = Expense.objects.get(pk=pk, user=request.user)
        expense.delete()
        messages.success(request, "Transaction deleted successfully!")
    except Expense.DoesNotExist:
        messages.error(request, "Transaction not found.")
    return redirect("transactions:transactions")


# ──────────────────────────────────────────────────
#  EDIT TRANSACTION
# ──────────────────────────────────────────────────
@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)

    if request.method == "POST":
        transaction_type = request.POST.get("type")
        amount = request.POST.get("amount")
        category = request.POST.get("category")
        description = request.POST.get("description")
        expense_date = request.POST.get("date")
        payment_mode = request.POST.get("payment")

        if not amount or not category or not expense_date:
            messages.error(request, "Please fill all required fields.")
            return redirect("transactions:edit_transaction", pk=pk)

        try:
            amount_val = float(amount)
            if amount_val <= 0:
                messages.error(request, "Amount must be greater than 0.")
                return redirect("transactions:edit_transaction", pk=pk)
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid amount.")
            return redirect("transactions:edit_transaction", pk=pk)

        old_created_at = expense.created_at.isoformat()

        expense.transaction_type = transaction_type
        expense.amount = amount
        expense.category = category
        expense.description = description
        expense.date = expense_date
        expense.payment_mode = payment_mode
        expense.save()

        collection = get_transactions_collection()
        collection.update_one(
            {"user_id": request.user.id, "created_at": old_created_at},
            {"$set": {
                "amount": float(amount),
                "category": category,
                "description": description,
                "date": expense_date,
                "transaction_type": transaction_type,
                "payment_mode": payment_mode,
            }}
        )

        messages.success(request, "Transaction updated successfully!")
        return redirect("transactions:transactions")

    # GET – load dynamic categories
    income_categories = Category.objects.filter(user=request.user, type="income")
    expense_categories = Category.objects.filter(user=request.user, type="expense")
    context = {
        "expense": expense,
        "income_categories": income_categories,
        "expense_categories": expense_categories,
    }
    return render(request, "transactions/edit-transaction.html", context)


# ──────────────────────────────────────────────────
#  CATEGORIES MANAGEMENT
# ──────────────────────────────────────────────────
@login_required
def categories_view(request):
    """List all categories + handle add new category."""
    user = request.user

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        cat_type = request.POST.get("type", "")

        if not name or not cat_type:
            messages.error(request, "Category name and type are required.")
            return redirect("transactions:categories")

        if cat_type not in ("income", "expense"):
            messages.error(request, "Invalid category type.")
            return redirect("transactions:categories")

        if Category.objects.filter(user=user, name=name, type=cat_type).exists():
            messages.error(request, f'Category "{name}" already exists for {cat_type}.')
            return redirect("transactions:categories")

        Category.objects.create(user=user, name=name, type=cat_type)
        messages.success(request, f'Category "{name}" added successfully!')
        return redirect("transactions:categories")

    income_categories = Category.objects.filter(user=user, type="income")
    expense_categories = Category.objects.filter(user=user, type="expense")

    context = {
        "income_categories": income_categories,
        "expense_categories": expense_categories,
    }
    return render(request, "transactions/categories.html", context)


@login_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Category name cannot be empty.")
            return redirect("transactions:categories")

        # Check for duplicate
        if Category.objects.filter(user=request.user, name=name, type=category.type).exclude(pk=pk).exists():
            messages.error(request, f'Category "{name}" already exists.')
            return redirect("transactions:categories")

        old_name = category.name
        category.name = name
        category.save()

        # Update existing transactions that used the old category name
        Expense.objects.filter(user=request.user, category=old_name).update(category=name)

        messages.success(request, f'Category renamed to "{name}"!')
        return redirect("transactions:categories")

    return redirect("transactions:categories")


@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)

    # Check if any transactions use this category
    txn_count = Expense.objects.filter(user=request.user, category=category.name).count()
    if txn_count > 0:
        messages.error(
            request,
            f'Cannot delete "{category.name}" — {txn_count} transaction(s) use it. '
            f'Rename or reassign them first.'
        )
        return redirect("transactions:categories")

    name = category.name
    category.delete()
    messages.success(request, f'Category "{name}" deleted!')
    return redirect("transactions:categories")


# ──────────────────────────────────────────────────
#  REPORTS & ANALYTICS
# ──────────────────────────────────────────────────
@login_required
def reports_view(request):
    user = request.user

    # ── Filters ──
    filter_from = request.GET.get("from", "")
    filter_to = request.GET.get("to", "")
    filter_category = request.GET.get("category", "")

    qs = Expense.objects.filter(user=user)

    if filter_from:
        qs = qs.filter(date__gte=filter_from)
    if filter_to:
        qs = qs.filter(date__lte=filter_to)
    if filter_category:
        qs = qs.filter(category=filter_category)

    # ── Summary totals ──
    total_income = qs.filter(transaction_type__iexact="income").aggregate(t=Sum("amount"))["t"] or 0
    total_expense = qs.filter(transaction_type__iexact="expense").aggregate(t=Sum("amount"))["t"] or 0
    net_savings = float(total_income) - float(total_expense)
    txn_count = qs.count()

    # ── Pie: Category-wise expense breakdown ──
    cat_data = (
        qs.filter(transaction_type__iexact="expense")
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    pie_labels = [d["category"] for d in cat_data]
    pie_values = [float(d["total"]) for d in cat_data]

    # ── Bar: Monthly income vs expense ──
    monthly_income = (
        qs.filter(transaction_type__iexact="income")
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )
    monthly_expense = (
        qs.filter(transaction_type__iexact="expense")
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    all_months = set()
    inc_map = {}
    exp_map = {}

    for item in monthly_income:
        label = item["month"].strftime("%b %Y")
        inc_map[label] = float(item["total"])
        all_months.add(item["month"])

    for item in monthly_expense:
        label = item["month"].strftime("%b %Y")
        exp_map[label] = float(item["total"])
        all_months.add(item["month"])

    sorted_months = sorted(all_months)[-12:]
    bar_labels = [m.strftime("%b %Y") for m in sorted_months]
    bar_income = [inc_map.get(l, 0) for l in bar_labels]
    bar_expense = [exp_map.get(l, 0) for l in bar_labels]

    # ── Line: Daily spending trend (last 30 days) ──
    thirty_days_ago = date.today() - timedelta(days=30)
    daily_data = (
        qs.filter(transaction_type__iexact="expense", date__gte=thirty_days_ago)
        .values("date")
        .annotate(total=Sum("amount"))
        .order_by("date")
    )
    daily_labels = [d["date"].strftime("%d %b") for d in daily_data]
    daily_values = [float(d["total"]) for d in daily_data]

    # ── Top 5 spending categories ──
    top_categories = (
        qs.filter(transaction_type__iexact="expense")
        .values("category")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")[:5]
    )
    top_cats = [
        {"name": d["category"], "total": float(d["total"]), "count": d["count"]}
        for d in top_categories
    ]

    # ── Payment mode breakdown ──
    payment_data = (
        qs.filter(transaction_type__iexact="expense")
        .values("payment_mode")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    pay_labels = [d["payment_mode"] for d in payment_data]
    pay_values = [float(d["total"]) for d in payment_data]

    # ── All categories for filter dropdown ──
    all_categories = Category.objects.filter(user=user).values_list("name", flat=True).distinct()

    context = {
        # Filters
        "filter_from": filter_from,
        "filter_to": filter_to,
        "filter_category": filter_category,
        "all_categories": all_categories,
        # Summary
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": net_savings,
        "txn_count": txn_count,
        # Pie chart
        "pie_labels": json.dumps(pie_labels),
        "pie_values": json.dumps(pie_values),
        # Bar chart
        "bar_labels": json.dumps(bar_labels),
        "bar_income": json.dumps(bar_income),
        "bar_expense": json.dumps(bar_expense),
        # Line chart (daily)
        "daily_labels": json.dumps(daily_labels),
        "daily_values": json.dumps(daily_values),
        # Payment mode
        "pay_labels": json.dumps(pay_labels),
        "pay_values": json.dumps(pay_values),
        # Top categories
        "top_cats": top_cats,
    }
    return render(request, "transactions/reports.html", context)