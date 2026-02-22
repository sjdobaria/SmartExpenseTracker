from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if not username or not password1 or not password2:
            messages.error(request, "All fields are required.")
            return redirect("accounts:signup_view")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("accounts:signup_view")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("accounts:signup_view")

        User.objects.create_user(username=username, password=password1)
        messages.success(request, "Account created successfully. Please login.")
        return redirect("accounts:login_view")
    return render(request, "accounts/signup.html")

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)  # 🔐 Django session login
            return redirect("dashboard:dashboard_view")
        else:
            messages.error(request, "Invalid credentials")

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("core:landing")
