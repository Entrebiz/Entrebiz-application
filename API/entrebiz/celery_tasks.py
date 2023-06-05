import datetime
import json
import logging
import requests
from Transactions.mixins import FindAccount
from celery.task import task
logger = logging.getLogger('lessons')
from utils.models import Currencies, Currencyconversionratescombined, Accounts, CurrencyConversionAPI

url = "https://freecurrencyapi.net/api/v2/latest"

def api_response(base_currency):
    for api in CurrencyConversionAPI.objects.filter(used=False):
        logger.info(f"APIKEY USED --> {api.key}")
        querystring = {
                "format": "json",
                "apikey": api.key,
                "base_currency": base_currency
            }
        resp = requests.request("GET", url, params=querystring)
        if resp.status_code == 200:
            logger.info(f"STATUS CODE --> {resp.status_code}")
            content = json.loads(resp.content)
            conversion_dict = content.get("data")
            return {
                'status' : True,
                'conversion_dict' : conversion_dict
            }
        else:
            api.used = True
            api.save()
            logger.info(f"STATUS CODE --> {resp.status_code}")
            logger.info(f"API call failed due to --> {resp.reason}")
            continue
    else:
        api = CurrencyConversionAPI.objects.all()
        api.update(used=False)
        return {
            'status' : False
        }

def currency_conversion():
    logger.info(f"-----------CURRENCY CONVERSION TASK STARTED----------")
    base_currency = "USD"
    logger.info(f"BASE CURRENCY --> {base_currency}")
    data = api_response(base_currency)
    if data.get('status'):
        conversion_dict = data.get('conversion_dict')
    else:
        logger.info(f"-----------CURRENCY CONVERSION TASK ENDED----------\n\n")
        return
    if conversion_dict:
        for base_key in conversion_dict:
            for to_key in conversion_dict:
                to_currency = conversion_dict[to_key]
                base_currency = conversion_dict[base_key]
                conversionrate = format(to_currency/base_currency,".6f")
                try:
                    tocurrency = Currencies.objects.get(code=to_key)
                    fromcurrency = Currencies.objects.get(code=base_key)
                    c_conversion,created = Currencyconversionratescombined.objects.get_or_create(fromcurrency=fromcurrency,tocurrency=tocurrency)
                    c_conversion.conversionrate = conversionrate
                    c_conversion.save()
                    print("created\n------------------------\n")
                    logger.info(f"CREATED --> {fromcurrency} -> {tocurrency} = {conversionrate}")
                except Exception as e:
                    print(f"Not created : {e}\n------------------------\n")
                    pass
    logger.info(f"-----------CURRENCY CONVERSION TASK ENDED----------\n\n")

def create_transaction_for_master_acc(last_transactionno,master_account_obj,converted_total_deduction_amount,int_transaction, affiliate_fee_note=None):
    from utils.models import Transactions,Transactiontypes
    Transactiontypes.objects.get_or_create(name='International Transfer Fee to Master Account')
    try:
        master_transaction_obj = Transactions.objects.create(
                                transactionno=int(last_transactionno) + 1,
                                toaccount=master_account_obj,
                                fromamount=converted_total_deduction_amount,
                                toamount=converted_total_deduction_amount,
                                transactiontype=Transactiontypes.objects.get(name='International Transfer Fee to Master Account'),
                                parenttransaction = int_transaction.transaction,
                                note=f"AC - {int_transaction.transaction.fromaccount.accountno}{affiliate_fee_note if affiliate_fee_note else ''}",
                                toaccountbalance=master_account_obj.balance,
                                fromaccountbalance=master_account_obj.balance,
                                amount_type="Admin Fee",
                            )
        int_transaction.master_fee_deducted = True
        int_transaction.save()
    except Exception as e:
        logger.info(f"{e}")




def check_transaction_status():
    from utils.models import Internationaltransactions,Transactions,Transactiontypes
    from Transactions.mixins import TransactionMixins,ModelQueries
    from django.db.models import Q
    from decimal import Decimal
    from entrebiz import settings
    current_date = datetime.datetime.now().date()
    for int_transaction in Internationaltransactions.active.filter(Q(affiliate_fee_deducted=False) | Q(master_fee_deducted=False),verificationstatus="Executed",hideforadmin=False):
        days_difference = current_date - int_transaction.createdon.date()
        if days_difference.days >= settings.FEE_CALCULATE_MINIMUM_DURATION:
            affiliate_amount = TransactionMixins().get_affiliate_amount(int_transaction.transaction)
            try:
                if affiliate_amount and int_transaction.transaction.fromaccount.user_account.referred_by:
                    referred_by_user = int_transaction.transaction.fromaccount.user_account.referred_by
                    account_obj,converted_affiliate_amount = FindAccount().find_affiliate_account_convert_amount(referred_by_user,int_transaction.transaction.fromaccount.currency,affiliate_amount)
                    if not int_transaction.affiliate_fee_deducted and account_obj and converted_affiliate_amount:
                        try:
                            account_obj.balance += Decimal(converted_affiliate_amount)
                            account_obj.save()
                            try:
                                last_transactionno = Transactions.objects.latest('transactionno').transactionno
                            except Exception as e:
                                logger.info(e)
                                last_transactionno = 10000000
                            af_transaction_obj = Transactions.objects.create(
                                transactionno=int(last_transactionno) + 1,
                                toaccount=account_obj,
                                fromamount=converted_affiliate_amount,
                                toamount=converted_affiliate_amount,
                                transactiontype=Transactiontypes.objects.get(name='Affiliate Fee'),
                                note="Affiliate fee",
                                toaccountbalance=account_obj.balance,
                            )
                            int_transaction.affiliate_fee_deducted = True
                            int_transaction.save()
                        except Exception as e:
                            logger.info("Add Affiliate Fee : error : ",e)
                            pass
                    if not int_transaction.master_fee_deducted:
                        try:
                            transaction_amounts = ModelQueries().get_transaction_amounts(int_transaction.transaction)
                            wire_fee = transaction_amounts.get("wire_fee")
                            conversion_fee = transaction_amounts.get("conversion_fee")
                            cable_charge = transaction_amounts.get("cable_charge")
                            rem_wire_fee = float(wire_fee) - float(affiliate_amount)
                            total_deduction_amount = float(conversion_fee) + float(cable_charge) + float(rem_wire_fee)
                            master_account_obj,converted_total_deduction_amount = FindAccount().find_master_account_convert_amount(int_transaction.transaction.fromaccount, total_deduction_amount, int_transaction.transaction.fromaccount.user_account.test_account)
                            master_account_obj.balance += Decimal(converted_total_deduction_amount)
                            master_account_obj.save()

                            try:
                                last_transactionno = Transactions.objects.latest('transactionno').transactionno
                            except Exception as e:
                                logger.info(e)
                                last_transactionno = 10000000
                            affiliate_fee_note = ' | Affiliate fee deducted'
                            create_transaction_for_master_acc(last_transactionno,master_account_obj,converted_total_deduction_amount,int_transaction,affiliate_fee_note=affiliate_fee_note)
                            int_transaction.master_fee_deducted = True
                            int_transaction.save()
                        except Exception as e:
                            logger.info("Add Master fee : error : ",e)
                            pass
                elif not int_transaction.master_fee_deducted:
                    try:
                        transaction_amounts = ModelQueries().get_transaction_amounts(int_transaction.transaction)
                        wire_fee = transaction_amounts.get("wire_fee")
                        conversion_fee = transaction_amounts.get("conversion_fee")
                        cable_charge = transaction_amounts.get("cable_charge")
                        total_deduction_amount = float(conversion_fee) + float(cable_charge) + float(wire_fee)
                        master_account_obj,converted_total_deduction_amount = FindAccount().find_master_account_convert_amount(int_transaction.transaction.fromaccount, total_deduction_amount, int_transaction.transaction.fromaccount.user_account.test_account)
                        master_account_obj.balance += Decimal(converted_total_deduction_amount)
                        master_account_obj.save()

                        try:
                            last_transactionno = Transactions.objects.latest('transactionno').transactionno
                        except Exception as e:
                            logger.info(e)
                            last_transactionno = 10000000
                        create_transaction_for_master_acc(last_transactionno,master_account_obj,converted_total_deduction_amount,int_transaction)
                        int_transaction.master_fee_deducted = True
                        int_transaction.affiliate_fee_deducted = True
                        int_transaction.save()
                    except Exception as e:
                        logger.info("Add Master fee : error : ",e)
                        pass
            except Exception as e:
                logger.info(f"WIRE TRANSACTION - {int_transaction.id} : error :",e)
                pass


