from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Expense
from django.contrib import messages
from datetime import date
from .mongo import get_transactions_collection


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

    return render(request, "transactions/add-transaction.html")


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
        # filter_month comes as "YYYY-MM"
        try:
            year, month = filter_month.split("-")
            qs = qs.filter(date__year=int(year), date__month=int(month))
        except ValueError:
            pass

    context = {
        "transactions": qs,
        "filter_category": filter_category,
        "filter_type": filter_type,
        "filter_month": filter_month,
    }
    return render(request, "transactions/transactions.html", context)


@login_required
def delete_expense(request, pk):
    try:
        expense = Expense.objects.get(pk=pk, user=request.user)
        expense.delete()
        messages.success(request, "Transaction deleted successfully!")
    except Expense.DoesNotExist:
        messages.error(request, "Transaction not found.")
    return redirect("transactions:transactions")


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

        # Store old date for MongoDB lookup
        old_created_at = expense.created_at.isoformat()

        # Update Django ORM
        expense.transaction_type = transaction_type
        expense.amount = amount
        expense.category = category
        expense.description = description
        expense.date = expense_date
        expense.payment_mode = payment_mode
        expense.save()

        # Update MongoDB as well
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

    context = {
        "expense": expense,
    }
    return render(request, "transactions/edit-transaction.html", context)