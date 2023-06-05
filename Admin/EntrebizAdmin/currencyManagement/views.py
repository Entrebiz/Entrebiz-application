import logging
import json
from django.views import View
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from EntrebizAdmin.decorators import admin_only
from Transactions.mixins import ModelQueries, add_log_action

from utils.models import Currencies, Currencyconversionmargins
logger = logging.getLogger('lessons')

@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only,name='dispatch')
class CurrencyManagement(View,ModelQueries):  
    def get(self, request):
        currcnmargins = Currencyconversionmargins.objects.filter(isdeleted=False).order_by('id')
        currcnmargins = self.paginate(currcnmargins, page=1,per_page=100)
        currencies = Currencies.objects.filter(isdeleted=False).order_by('code')
        context = {
            'currcnmargins' : currcnmargins,
            'currencies' : currencies
        }
        return render(request,'currency-management/currency-management.html',context)
    def post(self ,request):
        response = {}
        if request.POST.get('action_type') == 'getcurrency_bypage':
            currcnmargins = Currencyconversionmargins.objects.filter(isdeleted=False).order_by('id')
            currcnmargins = self.paginate(currcnmargins,page=request.POST.get("page",1),per_page=100)
            context =  {
                'currcnmargins' : currcnmargins
            }
            response['currency_table'] = render_to_string('currency-management/currency-table.html',context)
            return JsonResponse(response)
        
        elif request.POST.get('action_type') == 'currency_search':
            from_curr_code = request.POST.get('FromCurrencyCode')
            to_curr_code = request.POST.get('ToCurrencyCode')
            currcnmargins = Currencyconversionmargins.objects.filter(isdeleted=False).order_by('id')
            currencies = Currencies.objects.filter(isdeleted=False)
            if from_curr_code:
                currcnmargins = currcnmargins.filter(fromcurrency__code=from_curr_code,isdeleted=False)
            if to_curr_code:
                currcnmargins = currcnmargins.filter(tocurrency__code=to_curr_code,isdeleted=False)
            currcnmargins = self.paginate(currcnmargins, page=1,per_page=100)
            context = request.POST.dict()
            context['currcnmargins'] = currcnmargins
            context['currencies'] = currencies.order_by('code')
            return render(request,'currency-management/currency-management.html',context)
        elif request.POST.get('action_type') == 'save_margin_percents':
            status = ''
            message = ''
            for data in json.loads(request.POST.get('marginUpdates')):
                if data.get('marginId') and str(data.get('marginPercent')):
                    try:
                        currcnmargins = Currencyconversionmargins.objects.get(id=data.get('marginId'))
                        currcnmargins.marginpercent = data.get('marginPercent')
                        currcnmargins.modifiedby = request.user
                        currcnmargins.save()
                        add_log_action(request, currcnmargins, status=f"currency conversion({currcnmargins.fromcurrency.code} -> {currcnmargins.tocurrency.code}) margin has been updated with {currcnmargins.marginpercent}%", status_id=2)
                        message = 'Margins updated successfully'
                        status = True
                    except Exception as e:
                        logger.info(e)
                        message = 'Something went wrong'
                        status = False
            currcnmargins = Currencyconversionmargins.objects.filter(isdeleted=False).order_by('id')
            currcnmargins = self.paginate(currcnmargins, page=1,per_page=100)
            currencies = Currencies.objects.filter(isdeleted=False)
            context = {
                'currcnmargins' : currcnmargins,
                'currencies' : currencies.order_by('code'),
                'status' : status,
                'message' : message,
            }
            return render(request,'currency-management/currency-management.html',context)