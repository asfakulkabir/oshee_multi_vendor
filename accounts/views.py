from django.shortcuts import render



def become_vendor(request):
    return render(request, 'accounts/become_vendor.html')