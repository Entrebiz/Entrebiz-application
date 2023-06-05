
from logging import exception
from django.shortcuts import render, redirect
from django.views import View
from utils.models import Documenttypes, Documenttypesforverification,\
     Documentfields,Customerdocuments,Customers,Customerdocumentfiles,Useraccounts,Customerdocumentdetails,Businessdetails
from django.http import JsonResponse, response
import datetime
from datetime import datetime as dt
from django.conf import settings
import os
import logging
logger = logging.getLogger('lessons')
class DocumentFields(View):
    def get(self,request):
        if request.GET.get('for_field'):
            
            documenttype = Documenttypes.objects.get(id=request.GET.get('id_proof'),isdeleted=False)
            doc_fileds = Documentfields.objects.filter(documenttype=documenttype,isdeleted=False).values()
            response = {
                'doc_fileds' : list(doc_fileds),
            }
            return JsonResponse(response)



class CompanyVerificationView(View):
    def get(self,request):
        customer_docs = Customerdocuments.objects.filter(customer__user=request.user,verificationtype__verificationtype=3,isdeleted=False)
        if customer_docs.exists():
            user_status = Useraccounts.objects.get(customer__user=request.user).activestatus
            document_details = Customerdocumentdetails.objects.filter(customerdocument=customer_docs[0])
            context={
                'user_status' : user_status,
                'customer_docs' : customer_docs[0] if customer_docs else "",
                'document_details':document_details
            }
            
            if request.session.get('success_message'):
                context.update({
                    'message' : request.session.get('success_message'),
                    'status':request.session.get('status')
                })
                del request.session['success_message']
                del request.session['status']
            return render(request,'companyVerification/companyVerification.html',context)
        else:
            return redirect('CompanyEdit')
    def post(self,request):
        pass


class CompanyEdit(View):
    def get(self,request):
        try:
            customer_docs = Customerdocuments.objects.filter(customer__user=request.user,verificationtype__verificationtype=3,isdeleted=False)
            document_details_value1 = Customerdocumentdetails.objects.get(customerdocument=customer_docs[0],
                    field__fieldtype=2,customerdocument__documenttype__name="Registration certificate"
            )
            document_details_value2 = Customerdocumentdetails.objects.get(customerdocument=customer_docs[0],
                    field__fieldtype=5,customerdocument__documenttype__name="Registration certificate"
            )
            date_of_incorporation = (document_details_value2.value).split()
        except Exception as e:
            logger.info(e)
            customer_docs=''
            document_details_value1=''
            document_details_value2=''
        months_choices = []
        year = datetime.datetime.today().year
        year_choices = list(range(year - 1, year - 16, -1))
        for i in range(1,13):
            months_choices.append(datetime.date(2022, i, 1).strftime('%B'))
        days_choices = [day for day in range(1,32)]
        company_docs = Documenttypesforverification.objects.filter(verificationtype=3)
        context = {
            'idProof':customer_docs[0].documenttype.id if customer_docs else "",
            'company_docs' : company_docs,
            'year_choices' : year_choices,
            'months_choices' : months_choices,
            'days_choices' : days_choices,
            'customer_docs' : customer_docs[0] if customer_docs else "",
            'docId':document_details_value1.value if document_details_value1 else "",
            'companyMonth':date_of_incorporation[0] if document_details_value2 else "",
            'companyYear':date_of_incorporation[2] if document_details_value2 else "",
            'companyDay': date_of_incorporation[1][:-1] if document_details_value2 else "",
            'label_name': document_details_value1.field.fieldname if document_details_value1 else ""
            }
        if request.session.get('page_check_token'):
            return render(request,'companyVerification/companyVerification-edit.html',context)
        else:
            return render(request,'companyVerification/companyVerification-edit-app.html',context)
    def post(self,request):
        customer_doc=Customerdocuments.objects.filter(
                customer__user=request.user,verificationtype__verificationtype=3).first()
        year = dt.today().year
        year_choices = list(range(year - 1, year - 16, -1))
        days_choices = [day for day in range(1,32)]
        months_choices = []
        for i in range(1,13):
            months_choices.append(datetime.date(2008, i, 1).strftime('%B'))
        request.session['company_verification_document']=request.POST.dict()
        context = {}
        def validate():
            verification_type = request.POST.get('VerificationType')
            customer_doc=Customerdocuments.objects.filter(
                customer__user=request.user,verificationtype__verificationtype=3).first()
            if not request.FILES.get('frontPage') and not customer_doc:
                return{
                    'status' : False,
                    'message' : 'please choose document',
                    }
            else:
                
                try:
                    ext = os.path.splitext(request.FILES.get('frontPage').name)[1]
                    filesize = request.FILES.get('frontPage').size
                    if not ext in settings.ALLOWED_FORMATS:
                            return {
                                'status' : False,
                                'message' : 'Incorrect file format',
                                }
                    elif filesize > settings.MAX_FILE_SIZE:
                        return {
                            'status' : False,
                            'message' : 'Maximum file size allowed is 10 MB',
                            }
                except Exception as e:
                    logger.info(e)
                    pass
               
                if customer_doc:
                    current_user = Useraccounts.objects.get(customer__user=request.user)
                    business_detail = Businessdetails.objects.get(customer__user=request.user)
                    all_business_detail = Businessdetails.objects.filter(companyname=business_detail.companyname,
                                                url=business_detail.url)
                    all_customers_list = []
                    for customer_each in all_business_detail:
                        all_customers_list.append(customer_each.customer)

                    if request.POST.get('idProof'):
                        for customer in all_customers_list:
                            customer_doc=Customerdocuments.objects.get(customer=customer,verificationtype__verificationtype=3)
                            customer_doc.documenttype = Documenttypes.objects.get(id=int(request.POST.get('idProof')))
                            customer_doc.save()
                        
                    if request.POST.get('docId'):
                        for customer in all_customers_list:
                            customer_doc=Customerdocuments.objects.filter(
                                    customer=customer,verificationtype__verificationtype=3).first()
                            customer_document_details1=Customerdocumentdetails.objects.get(customerdocument=customer_doc,
                                    field = Documentfields.objects.get(fieldtype='2',documenttype__description="Company registration document"))
                            customer_document_details1.value= request.POST.get('docId')     
                            customer_document_details1.save()
                        
                    if request.POST.get('companyMonth') or request.POST.get('companyDay') or request.POST.get('companyYear'):
                        for customer in all_customers_list:
                            customer_doc=Customerdocuments.objects.filter(
                                    customer=customer,verificationtype__verificationtype=3).first()
                            customer_document_details2 = Customerdocumentdetails.objects.get(
                                        customerdocument=customer_doc,
                                        field = Documentfields.objects.get(fieldtype='5',documenttype__description="Company registration document"),
                                    )
                            customer_document_details2.value= str(request.POST.get('companyMonth'))+" "+str(request.POST.get('companyDay'))+", "+str(request.POST.get('companyYear')) 
                            customer_document_details2.save() 

                    if request.FILES.get('frontPage'):
                        for customer in all_customers_list:
                            customer_doc=Customerdocuments.objects.filter(
                                    customer=customer,verificationtype__verificationtype=3).first()
                            customer_files = Customerdocumentfiles.objects.get(
                                            customerdocument=customer_doc) 
                            customer_files.filelocation = request.FILES.get('frontPage')
                            customer_files.save()
                         
                    return{
                            'status' : True,
                            'message' : 'Updated successfully',
                            }
                else:  
                    current_user = Useraccounts.objects.get(customer__user=request.user)
                    business_detail = Businessdetails.objects.get(customer__user=request.user)
                    all_business_detail = Businessdetails.objects.filter(companyname=business_detail.companyname,
                                                url=business_detail.url)
                    all_customers_list = []
                    for customer_each in all_business_detail:
                        all_customers_list.append(customer_each.customer)
                        
                    for customer in all_customers_list:
                        customer_doc = Customerdocuments.objects.create(
                                    customer=customer,verificationtype=Documenttypesforverification.objects.get(documenttype__id=request.POST.get('idProof')),
                                    documenttype = Documenttypes.objects.get(id=int(request.POST.get('idProof')))
                                    )
                        customer_document_details1 = Customerdocumentdetails.objects.create(
                                    customerdocument=customer_doc,value=request.POST.get('docId'),
                                    field = Documentfields.objects.get(fieldtype='2',documenttype__description="Company registration document"),

                                )
                        customer_document_details2 = Customerdocumentdetails.objects.create(
                                    customerdocument=customer_doc,value=str(request.POST.get('companyMonth'))+" "+str(request.POST.get('companyDay'))+", "+str(request.POST.get('companyYear')),
                                    field = Documentfields.objects.get(fieldtype='5',documenttype__description="Company registration document"),

                                )
                        customer_files = Customerdocumentfiles.objects.create(
                                    customerdocument=customer_doc,filelocation=request.FILES.get('frontPage')
                                )
                
                    return{
                            'status' : True,
                            'message' : 'Uploaded successfully',
                            }
        response = validate()
        if response and not response.get('status'):
            request.session['address_verify_message'] = response.get('message')
            context = request.POST.dict()
            context.update({
            'message' : response.get('message'),
            'status' : False,
            'company_docs' : Documenttypesforverification.objects.filter(verificationtype=3),
            'months_choices' : months_choices,
            'year_choices' : year_choices,
            'days_choices' : days_choices,
            })
            if request.session.get('page_check_token'):
                return render(request,'companyVerification/companyVerification-edit.html',context)
            else:
                return render(request,'companyVerification/companyVerification-edit-app.html',context)
        elif response.get('status'):
            if request.session.get('page_check_token'):
                del request.session['page_check_token']
                return redirect('/pageStatus/?page=1')
            else:
                request.session['success_message']=response.get('message')
                request.session['status']=response.get('status')
                return redirect('CompanyList')
            
        