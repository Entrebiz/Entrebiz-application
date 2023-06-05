import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View

from EntrebizAdmin.decorators import admin_only
from Transactions.mixins import ModelQueries, add_log_action
from utils.models import Countries

logger = logging.getLogger("lessons")


@method_decorator(login_required, name="dispatch")
@method_decorator(admin_only, name="dispatch")
class CountryManagementView(View, ModelQueries):
    def get(self, request):
        countries = Countries.objects.all().order_by("name")
        context = {"countries": self.paginate(countries, page=1, per_page=100)}
        if request.session.get("countrySuccMsg"):
            context["status"] = True
            context["message"] = request.session.get("countrySuccMsg")
            del request.session["countrySuccMsg"]
        return render(request, "country-management/country-management.html", context)

    def post(self, request):
        response = {}
        if request.POST.get("action_type") == "getcountry_bypage":
            countries = Countries.objects.all().order_by("name")
            context = {"countries": self.paginate(countries, page=request.POST.get("page", 1), per_page=100)}
            response["country_table"] = render_to_string("country-management/country-table.html", context)
            return JsonResponse(response)

        elif request.POST.get("action_type") == "country_search":
            name = request.POST.get("name")
            shortform = request.POST.get("shortform")
            countrycode = request.POST.get("countrycode")
            filter_params = {}
            if name:
                filter_params["name__icontains"] = name
            if shortform:
                filter_params["shortform__icontains"] = shortform
            if countrycode:
                filter_params["phonecode__icontains"] = countrycode
            if filter_params:
                countries = Countries.objects.filter(**filter_params).order_by("name")
            else:
                countries = Countries.objects.all().order_by("name")
            context = {"countries": self.paginate(countries, page=1, per_page=request.POST.get("per_page", 100))}
            response["country_table"] = render_to_string("country-management/country-table.html", context)
            return JsonResponse(response)
        elif request.POST.get("action_type") == "disable_or_enable":
            context = {"countries": Countries.objects.all().order_by("name")[:100]}
            id = request.POST.get("country_id")
            type_disable_or_enable = request.POST.get("type_disable_or_enable")
            to_be_delete = False
            if type_disable_or_enable == "0":
                to_be_delete = True
            try:
                country = Countries.objects.get(id=id)
                country.isdeleted = to_be_delete
                country.save()
                if country.isdeleted:
                    add_log_action(
                        request,
                        country,
                        status=f"Country {country} has been disabled by {request.user.email}",
                        status_id=3,
                    )
                    context["message"] = f"{country.name} Disabled Successfully"
                else:
                    add_log_action(
                        request,
                        country,
                        status=f"Country {country} has been enabled by {request.user.email}",
                        status_id=2,
                    )
                    context["message"] = f"{country.name} Enabled Successfully"
                context["status"] = True
            except Exception as e:
                logger.info(f"{e}")
                context["message"] = "Error Occured"
                context["status"] = False
            return render(request, "country-management/country-management.html", context)


@method_decorator(login_required, name="dispatch")
@method_decorator(admin_only, name="dispatch")
class ViewCountry(View):
    def get(self, request):
        try:
            id = request.GET.get("id")
            country = Countries.objects.get(id=id)
            country_name = country.name
            shortform = country.shortform
            countrycode = country.phonecode
            context = {
                "country_name": country_name,
                "shortform": shortform,
                "countrycode": countrycode,
            }
            return render(request, "country-management/edit-country.html", context)
        except Exception as e:
            logger.info(f"{e}")
            return redirect("/country-management")

    def post(self, request):
        id = request.POST.get("id")
        country_name = request.POST.get("country_name").strip()
        shortform = request.POST.get("shortform").strip()
        countrycode = request.POST.get("countrycode").strip()

        def validate():
            if not country_name:
                return {"status": False, "message": "Country Name is required."}
            elif not shortform:
                return {"status": False, "message": "Shortform is required."}
            elif not countrycode:
                return {"status": False, "message": "Phonecode is required."}
            try:
                country = Countries.objects.get(id=id)
                country.name = country_name
                country.shortform = shortform
                country.phonecode = countrycode
                country.save()
                add_log_action(
                    request,
                    country,
                    status=f'Country "{country.name}" has been edited',
                    status_id=2,
                )
                return {
                    "status": True,
                    "message": "Country details updated successfully",
                }
            except Exception as e:
                logger.info(f"{e}")
                return {"status": False, "message": "Error Occured"}

        data = validate()
        context = {}
        if data.get("status"):
            request.session["countrySuccMsg"] = data.get("message")
            return redirect("/country-management")
        else:
            context = request.POST.dict()
            context["message"] = data.get("message")
            context["status"] = data.get("status")
            return render(request, "country-management/edit-country.html", context)


@method_decorator(login_required, name="dispatch")
@method_decorator(admin_only, name="dispatch")
class AddCountryView(View):
    def get(self, request):
        return render(request, "country-management/add-country.html")

    def post(self, request):
        country_name = request.POST.get("country_name").strip()
        shortform = request.POST.get("shortform").strip()
        countrycode = request.POST.get("countrycode").strip()

        def validate():
            if not country_name:
                return {"status": False, "message": "Country Name is required."}
            elif not shortform:
                return {"status": False, "message": "Shortform is required."}
            elif not countrycode:
                return {"status": False, "message": "Country code is required."}
            try:
                country, created = Countries.objects.get_or_create(
                    name=country_name
                )
                if not created:
                    return {"status": False, "message": "Country with same name already exists."}
                country.shortform = shortform
                country.phonecode = countrycode
                country.save()
                if created:
                    add_log_action(
                        request,
                        country,
                        status=f'Country "{country.name}" has been added',
                        status_id=1,
                    )
                return {"status": True, "message": "Country added successfully"}
            except Exception as e:
                logger.info(f"{e}")
                return {"status": False, "message": "Error Occured"}

        data = validate()
        if data.get("status"):
            request.session["countrySuccMsg"] = data.get("message")
            return redirect("/country-management")
        else:
            context = request.POST.dict()
            context["message"] = data.get("message")
            context["status"] = data.get("status")
            context["countries"] = Countries.objects.all().order_by("name")[:100]
            return render(request, "country-management/add-country.html", context)
