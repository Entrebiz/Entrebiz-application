from django.shortcuts import render
from django.views import View

# Create your views here.
class AboutUs(View):
    def get(self, request):
        return render(request,'company-info/about-us.html')

class Services(View):
    def get(self, request):
        return render(request,'company-info/services.html')

class TermsAndCondition(View):
    def get(self, request):
        return render(request,'company-info/terms-and-condition.html')

class PrivacyPolicy(View):
    def get(self, request):
        return render(request,'company-info/privacy-policy.html')