from rest_framework.response import Response
from rest_framework.views import APIView
from decimal import Decimal
from Transactions.mixins import checkNonAsciiChracters, add_log_action, FindAccount
from api.v1.externalapiaccounttoaccount.serializers import AccountToAccountApiSerilaizer
from api.v1.serializers import AccountToAccountSerilaizer
from api.v1.utils.permissions import APIAccessTokenPermissions, TransactionPermission, \
    AccountVerifiedPermission, AccountTransactionPermission, AccountlockedPermission, AccountlockedPermissionforextapi
from utils.models import Currencyconversionmargins, Currencyconversionratescombined, Accounts, Internalbeneficiaries, \
    Transactiontypes, Transactions
from rest_framework import status


class ExternalAccountToAccountAPIView(APIView,FindAccount):
    authentication_classes = [APIAccessTokenPermissions]
    permission_classes = [AccountVerifiedPermission,AccountlockedPermissionforextapi,AccountTransactionPermission]


    def post(self, request):
        serializer = AccountToAccountApiSerilaizer(data=request.data)
        if serializer.is_valid():
            context = {}
            debitaccount_number = request.data.get('debit_account')
            try:
                debit_account = Accounts.objects.get(accountno=debitaccount_number,createdby=request.user)
            except Exception as e:
                # logger.info(e)
                context = {
                "status": False,
                "errors": {
                    "debit_account": [
                        "Invalid debit account!"
                    ]
                },
                "message": "Invalid data"
            }
                # return redirect('accTransaction')
                return Response(context,status=status.HTTP_404_NOT_FOUND)
            ben_acc_number = request.data.get('beneficiary_account')
            if ben_acc_number in list(
                    Accounts.objects.filter(accountno=ben_acc_number, isdeleted=False,
                                            createdby=request.user).values_list(
                        'accountno', flat=True)):
                context = {
                    'status': False,
                    "errors": {
                        "beneficiary_account": [
                            "Both accounts cannot be the same user!"
                        ]
                    },
                    'message': 'validation error',
                }
                return Response(context,status=status.HTTP_404_NOT_FOUND)
            note = request.data.get('note')
            if not checkNonAsciiChracters(note):
                context = {
                    "status": False,
                    "errors": {
                        "note": [
                            "Fancy Characters are not allowed"
                        ]
                    },
                    "message": "Invalid data"
                }
                return Response(context,status=status.HTTP_404_NOT_FOUND)
            if float(request.data.get('amount')) < float(debit_account.balance):
                beneficiaryaccount_number = request.data.get('beneficiary_account')
                try:
                    internal_beneficiary = Internalbeneficiaries.objects.get(createdby=request.user,
                                                                             account=Accounts.objects.get(
                                                                                 accountno=beneficiaryaccount_number),
                                                                             isdeleted=False)
                    beneficiary_name = internal_beneficiary.receivername
                except Exception as e:
                    # logger.info(e)
                    beneficiary_name = ''
                benefiary_account = Accounts.objects.get(accountno=beneficiaryaccount_number)
                from_amount = round(Decimal(request.data.get('amount')), 2)
                if debit_account.currency.code == benefiary_account.currency.code:
                    conversionfee = Decimal(0.00)
                else:
                    conversionfee = round(from_amount * Decimal(0.5 / 100), 2)
                try:
                    currency_conversion = Currencyconversionratescombined.objects.get(
                        fromcurrency__code=debit_account.currency.code,
                        tocurrency__code=benefiary_account.currency.code,
                        isdeleted=False)
                except Exception as e:
                    # logger.info(e)
                    context = {
                        'status': False,
                        'message': 'Having trouble with selected account! Please try with another.',
                    }
                    return Response(context)
                conversionrate = round(currency_conversion.conversionrate, 4)
                try:
                    currency_margin = Currencyconversionmargins.objects.get(
                        fromcurrency__code=debit_account.currency.code,
                        tocurrency__code=benefiary_account.currency.code,
                        isdeleted=False)
                    margin_rate = currency_margin.marginpercent
                    conversionrate = conversionrate - (conversionrate * Decimal(float(margin_rate) / 100))
                except Exception as e:
                    # logger.info(e)
                    pass

                creditamount = round(from_amount * conversionrate, 2)
                debitamount = from_amount + conversionfee
                if debitamount > float(debit_account.balance):
                    context = {
                        'status': False,
                        'message': 'Insufficient Balance',
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                context['status'] = True

                def validation_fn():
                    try:
                        debit_account_number = debitaccount_number
                        try:
                            debit_account = Accounts.objects.get(accountno=debit_account_number)
                            debit_account_code = debit_account.currency.code
                        except Exception as e:
                            return {
                                'status':False,
                                'message':'Invalid debit account',
                                'debit_account':True
                            }
                        beneficiary_account_number = beneficiaryaccount_number
                        try:
                            credit_account = Accounts.objects.get(accountno=beneficiary_account_number)
                            beneficiary_code = credit_account.currency.code
                        except Exception as e:
                            return {

                                'status':False,
                                'message':'invalid credit account',
                                'credit_account':True
                            }
                        note = request.data.get('note')
                        try:
                            internal_beneficiary = Internalbeneficiaries.objects.get(createdby=request.user,
                                                                                     account=Accounts.objects.get(
                                                                                         accountno=beneficiary_account_number),
                                                                                     isdeleted=False)
                            beneficiary_name = internal_beneficiary.receivername
                        except Exception as e:
                            # logger.info(e)
                            beneficiary_name = ''
                        debit_amount = Decimal(debitamount)
                        net_amount = Decimal(from_amount)
                        conversion_fee = Decimal(conversionfee)
                        credit_amount = Decimal(creditamount)
                        db_account_balance = debit_account.balance
                        if db_account_balance < debit_amount:
                            return {
                                'status': False,
                                'error': 'Your Transaction has been declined due to insufficient fund'
                            }
                        cr_account_balance = credit_account.balance
                        debit_accountbalance = Decimal(db_account_balance) - net_amount
                        credit_accountbalance = Decimal(cr_account_balance) + credit_amount
                        debit_account.balance = debit_accountbalance
                        debit_account.save()
                        credit_account.balance = credit_accountbalance
                        credit_account.save()
                        try:
                            account_number_prev = Transactions.objects.latest('transactionno').transactionno
                        except Exception as e:
                            # logger.info(e)
                            account_number_prev = 10000000
                        transactionno = int(account_number_prev) + 1

                        def create_transaction(transactionno, debit_account, credit_account, fromamount, toamount,
                                               debit_balance, credit_balance, amount_type, parent_transaction=None):
                            transaction_obj = Transactions.objects.create(
                                transactionno=transactionno,
                                fromaccount=debit_account,
                                toaccount=credit_account,
                                fromamount=fromamount,
                                toamount=toamount,
                                transactiontype=Transactiontypes.objects.get(name='Acccount To Account Transfer'),
                                createdby=request.user,
                                note=note,
                                recipientname=beneficiary_name,
                                fromaccountbalance=debit_balance,
                                toaccountbalance=credit_balance,
                                amount_type=amount_type,
                                parenttransaction=parent_transaction
                            )
                            add_log_action(request, transaction_obj,
                                           status=f"transaction(Account to Account : amount type {transaction_obj.amount_type}) created for account {str(transaction_obj.fromaccount.accountno)}",
                                           status_id=1)
                            return transaction_obj

                        try:
                            net_amount = net_amount
                            amount_type = "Net Amount"
                            parent_transaction = create_transaction(transactionno, debit_account, credit_account,
                                                                    net_amount,
                                                                    credit_amount,
                                                                    debit_accountbalance, credit_accountbalance,
                                                                    amount_type)
                        except Exception as e:
                            # logger.info(e)
                            return {
                                'status': False,
                                'error': 'Something went wrong! Please try again.'
                            }
                        try:
                            master_credit_account, converted_conversion_fee = self.find_master_account_convert_amount(
                                debit_account, conversion_fee, debit_account.user_account.test_account)
                            debit_account.balance -= Decimal(conversion_fee)
                            master_credit_account.balance += Decimal(converted_conversion_fee)
                            debit_account.save()
                            master_credit_account.save()
                            debit_balance = debit_account.balance
                            master_credit_balance = master_credit_account.balance

                            amount_type = "Conversion Fee"
                            create_transaction(transactionno, debit_account, master_credit_account, conversion_fee,
                                               converted_conversion_fee,
                                               debit_balance, master_credit_balance, amount_type, parent_transaction)

                        except Exception as e:
                            # logger.info(e)
                            return {
                                'status': False,
                                'error': 'Something went wrong! Please try again.'
                            }
                        return {
                            'status': True,
                            'transactionnumber': transactionno,
                            # 'transaction_id': parent_transaction.id,
                            'beneficiary_code':beneficiary_code,
                            'debit_account_code':debit_account_code,
                            'debit_account_number':debit_account_number,
                            'beneficiary_account_number':beneficiary_account_number,
                            'beneficiary_name':beneficiary_name,
                            'net_amount':net_amount,
                            'conversion_fee':conversion_fee,
                            'debit_amount':debit_amount,
                            'credit_amount':credit_amount,
                            'note':note
                        }
                    except Exception as e:
                        # logger.info(e)
                        context={}
                        return Response(context)

                response = validation_fn()
                if response.get('credit_account') == True:
                    context = {
                        'status': False,
                        'message': 'Invalid beneficiary account!'
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                if response.get('debit_account') == True:
                    context = {
                        'status': False,
                        'message': 'Invalid debit account!'
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)

                elif response.get('status') == True:
                    data = {
                        'transaction_details':{
                            'transaction_number': response.get('transactionnumber'),
                            'debit_amount': str(response.get('debit_amount')),
                            'beneficiary_name': response.get('beneficiary_name'),
                            'credit_amount': str(response.get('credit_amount')),
                            'net_amount': str(response.get('net_amount')),
                            'conversion_fee': str(response.get('conversion_fee')),
                            'note': response.get('note'),
                            'debit_account': {
                                'account_number': response.get('debit_account_number'),
                                'currency_code': response.get('debit_account_code'),
                            },
                            'credit_account': {
                                'account_number': response.get('beneficiary_account_number'),
                                'currency_code': response.get('beneficiary_code'),
                            },
                        }
                    }
                    context = {
                        'status': True,
                        'data': data,
                    }
                    return Response(context,status=status.HTTP_200_OK)
                if response.get('status') == False:
                    context = {
                        'error': True,
                        'message': response.get('error'),
                    }
                    return Response(context)
                if response and not response.get('status'):
                    context = {
                        'error': True,
                        'message': response.get('error'),
                    }
                    return Response(context)
            else:
                context = {
                    'status': False,
                    "errors": {
                        "amount": [
                            "Insufficient Balance"
                        ]
                    },
                    'message': 'validation error',
                }
                return Response(context,status=status.HTTP_404_NOT_FOUND)
        else:
            context = {}
            context['status'] = False
            context['errors'] = serializer.errors
            context['message'] = 'Invalid data'
            return Response(context,status=status.HTTP_404_NOT_FOUND)