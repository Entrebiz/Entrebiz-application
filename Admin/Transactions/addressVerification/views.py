from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.views import View
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from utils.models import Customerdocumentdetails, Customerdocumentfiles, Customerdocuments, Customers, Documentfields, Documenttypes, Documenttypesforverification, Useraccounts
import os
import logging
logger = logging.getLogger('lessons')


@method_decorator(login_required, name='dispatch')
class AddressVerification(View):
    def get(self, request):
        user_status = Useraccounts.objects.get(customer__user=request.user,isdeleted=False).activestatus
        customer_doc = Customerdocuments.objects.filter(customer__user=request.user,verificationtype__verificationtype=2,isdeleted=False)
        if customer_doc.exists():
            context = {
                'user_status' : user_status,
                'customer_doc' : customer_doc[0] if customer_doc else ""
            }
            if request.session.get('address_verify_message') and request.session.get('status'):
                context['message'] = request.session.get('address_verify_message')
                context['status'] = request.session.get('status')
                del request.session['address_verify_message']
                del request.session['status']
            return render(request, 'addressVerification/address-verification.html',context)
        else:
            return redirect('address-edit')

@method_decorator(login_required, name='dispatch')
class AddressEdit(View):
    def get(self,request):
        if request.GET.get('for_field'):
            documenttype = Documenttypes.objects.get(name=request.GET.get('id_proof'),description='Address verification proof')
            # doc_fileds = Documentfields.objects.get(documenttype__name=request.GET.get('id_proof'),isdeleted=False)
            doc_fileds = Documentfields.objects.get(documenttype=documenttype,isdeleted=False)
            response = {
                'doc_fileds' : model_to_dict(doc_fileds)
            }
            return JsonResponse(response)
        else:
            address_docs=Documenttypes.objects.filter(description='Address verification proof',isdeleted=False)
            try:
                customer_doc = Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=2,isdeleted=False)
                docValue=Customerdocumentdetails.objects.get(customerdocument=customer_doc).value
            except Exception as e:
                logger.info(e)
                docValue = ''
                customer_doc = ''
            context = {
                'address_docs' : address_docs,
                'customer_doc' : customer_doc,
                'docValue' : docValue
            }
            return render(request, 'addressVerification/address-edit.html', context)
    def post(self,request):
        def validate():
            if not request.POST.get('field_value'):
                return {
                'status' : False,
                'message' : 'please add bill number',
                }
            elif request.FILES.get('frontPage'):
                ext = os.path.splitext(request.FILES.get('frontPage').name)[1]
                filesize = request.FILES.get('frontPage').size
                valid_extensions = ['.jpeg','.jpg','.pdf','.tiff','.png']
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
            elif not request.FILES.get('frontPage'):
                try:
                    customer_doc=Customerdocuments.objects.get(customer__user=request.user,documenttype__name=request.POST.get('idProof'),isdeleted=False)
                    if customer_doc.documenttype.name == request.POST.get('idProof'):
                        pass
                    else:
                        return {
                        'status' : False,
                        'message' : 'please choose a document',
                        }
                except Exception as e:
                    logger.info(e)
                    return {
                        'status' : False,
                        'message' : 'please choose a document',
                        }
            try:
                customer_doc=Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=2,isdeleted=False)
                if customer_doc.documenttype.name == request.POST.get('idProof'):
                    pass
                else:
                    customer_doc.delete()
            except Exception as e:
                logger.info(e)
                pass
            customer_doc, created=Customerdocuments.objects.get_or_create(customer=Customers.objects.get(user=request.user),
                                    useraccount=Useraccounts.objects.get(customer__user=request.user),verificationtype=Documenttypesforverification.objects.get(documenttype__name=request.POST.get('idProof'),verificationtype=2),createdby=request.user,isdeleted=False)
            # customer_doc.verificationtype=Documenttypesforverification.objects.get(documenttype__name=request.POST.get('idProof'),verificationtype=2)
            customer_doc.documenttype=Documenttypes.objects.get(name=request.POST.get('idProof'),description='Address verification proof',isdeleted=False)
            customer_doc.save()
            doc_file_loc, created = Customerdocumentfiles.objects.get_or_create(customerdocument=customer_doc)
            if request.FILES.get('frontPage'):
                doc_file_loc.filelocation=request.FILES.get('frontPage')
                doc_file_loc.save()
            doc_details, created = Customerdocumentdetails.objects.get_or_create(customerdocument=customer_doc,createdby=request.user) 
            doc_details.field=Documentfields.objects.get(id=request.POST.get('doc_field_id'),isdeleted=False)
            doc_details.value = request.POST.get('field_value')
            doc_details.save()
            return {
                'status' : True,
                'message' : "Updated successfully"
            }
        response = validate()
        if response and not response.get('status'):
            if request.POST.get('page') == '3':
                if request.session.get('addressDetails'):
                    del request.session['addressDetails']
                if request.session.get('addressErrorMsg'):
                    del request.session['addressErrorMsg']
                request.session['addressErrorMsg'] = response.get('message')
                request.session['addressDetails'] = request.POST.dict()
                return redirect('/pageStatus/?page=3')
            request.session['address_verify_message'] = response.get('message')
            request.session['field_value'] = request.POST.get('field_value') if request.POST.get('field_value') else ""
            request.session['address_doc'] = request.POST.get('idProof') if request.POST.get('idProof') else ""

            address_docs=Documenttypes.objects.filter(description='Address verification proof',isdeleted=False)
            try:
                customer_doc = Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=2,isdeleted=False)
            except Exception as e:
                logger.info(e)
                customer_doc = ''
            context = {
                'address_docs' : address_docs,
                'customer_doc' : customer_doc ,
                'message' : response.get('message'),
                'docValue' : request.POST.get('field_value') if request.POST.get('field_value') else "" ,
                'ad_proof' : request.POST.get('idProof') if request.POST.get('idProof') else "" ,
                'status' : False

            }
            return render(request, 'addressVerification/address-edit.html', context)
        elif response.get('status'):
            if request.POST.get('page') == '3':
                return redirect('/dashboard')
            request.session['address_verify_message'] = response.get('message')
            request.session['status'] = True
            return redirect('address-list')
