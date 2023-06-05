from django.db.models import Q
import datetime
from rest_framework.response import Response
from rest_framework.views import APIView
from Transactions.mixins import ModelQueries
from api.v1.externalapitransactions.serializers import ExternalTransactionAPISerializer, TrasactionsAPISerializer
from api.v1.utils.pagination import CustomPagination
from api.v1.utils.permissions import APIAccessTokenPermissions
from utils.models import Accounts, Transactions
from rest_framework import status


class ExternalTransactionAPIView(APIView,ModelQueries,CustomPagination):
    authentication_classes = [APIAccessTokenPermissions]

    def post(self, request):
        serializer=ExternalTransactionAPISerializer(data=request.data)
        if serializer.is_valid():
            accountno = request.data.get("accountno").strip()
            transaction_no = request.data.get("transaction_no")
            beneficiary_name = request.data.get("beneficiary_name")
            from_date = request.data.get("from_date")
            if from_date:
                try:
                    datetime.datetime.strptime(from_date, "%Y-%m-%d")
                except:
                    context = {
                        "status": False,
                        "errors": {
                            "from_date": [
                                "Invalid date format"
                            ]
                        },
                        "message": "Invalid data"
                    }

                    return Response(context, status=status.HTTP_404_NOT_FOUND)
            to_date = request.data.get("to_date")
            if to_date:
                try:
                    datetime.datetime.strptime(to_date, "%Y-%m-%d")
                except:
                    context = {
                        "status": False,
                        "errors": {
                            "to_date": [
                                "Invalid date format"
                            ]
                        },
                        "message": "Invalid data"
                    }
                    return Response(context, status=status.HTTP_404_NOT_FOUND)
            try:
                account = Accounts.objects.get(accountno=accountno, user_account__customer__user=request.user)
            except:
                context ={
                    "status": False,
                    "errors": {
                        "accountno": [
                            "Invalid accountnumber"
                        ]
                    },
                    "message": "Invalid data"
                }

                return Response(context,status=status.HTTP_404_NOT_FOUND)
            if account:
                if not from_date and not to_date:
                    current_date = datetime.datetime.now()
                    prev_date = (datetime.datetime.now() - datetime.timedelta(days=30))
                    from_date = datetime.datetime.strftime(prev_date, "%Y-%m-%d")
                    to_date = datetime.datetime.strftime(current_date, "%Y-%m-%d")
                creditdebit = request.data.get("creditdebit_status")
                transactions = Transactions.active.filter(
                    Q(fromaccount=account) | Q(toaccount=account),
                    isdeleted=False)

                transactions = self.get_external_transactions(transactions, account=account,
                                                              transaction_no=transaction_no,
                                                              beneficiary_name=beneficiary_name,
                                                              from_date=from_date, to_date=to_date,
                                                              creditdebit=creditdebit)
                if not account.createdby.customer_details.all()[0].useracc_customer.all()[0].ismaster_account:
                    transactions = transactions.filter(~Q(amount_type="Conversion Fee")).exclude(
                        Q(toaccount__user_account__ismaster_account=True) &
                        ~Q(transactiontype__name="Third Party Transfer"))

                transactions = transactions.order_by("-id")
                # transactions = self.paginate_queryset(transactions, request)
                serializer = TrasactionsAPISerializer(transactions, many=True,
                                                   context={'account': account,
                                                            'request': request})
                data = {}
                if serializer.data:
                    data = serializer.data
                context = {
                    'status': True,
                    'data': data,
                }
                return Response(context,status=status.HTTP_200_OK)

            else:
                context = {
                    'status': False,
                    'message': 'Invalid accountnumber'
                }
                return Response(context,status=status.HTTP_404_NOT_FOUND)
        else:
            context = {
                'status':False,
                'error':serializer.errors,
                'message':'Invalid data'
            }
            return Response(context,status=status.HTTP_404_NOT_FOUND)

