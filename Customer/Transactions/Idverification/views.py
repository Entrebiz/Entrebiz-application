from django import db
from django.shortcuts import render, redirect
from django.views import View
from utils.models import Documenttypes, Documenttypesforverification,\
     Documentfields,Customerdocuments,Customers,Customerdocumentfiles,Useraccounts,Customerdocumentdetails
from django.http import JsonResponse, response
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
import json
from django.http import HttpResponse
from django.contrib import messages
import datetime
from datetime import datetime as dt
import os
from django.conf import settings
import logging
logger = logging.getLogger('lessons')

def getdocumentfeilds(request):
    document_value = request.POST.get("document_value")
    document_feilds = Documentfields.objects.filter(documenttype=Documenttypes.objects.get(id=document_value))
    response={}
    response['document_feilds'] = render_to_string("Idverification/form.html",
                                                         {"document_feilds": document_feilds
                                                          })
    return HttpResponse(json.dumps(response), content_type="application/json")

@method_decorator(login_required, name='dispatch')
class IdVerificationView(View):
    def get(self,request):
        customer_doc = Customerdocuments.objects.filter(customer__user=request.user,verificationtype__verificationtype=1)
        if customer_doc.exists():
            user_status = Useraccounts.objects.get(customer__user=request.user).activestatus
            value_list=[]
            validity=''
            idproofnumber=''
            try:
                customer_doc = Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=1)
                document_id = customer_doc.documenttype.id
                customerdocumentdetails = Customerdocumentdetails.objects.filter(customerdocument=customer_doc)
                customer_document_type=customer_doc.documenttype.id
                for customerdocumentdetail in customerdocumentdetails:
                    if customerdocumentdetail.field.fieldtype == 5:
                        validity = customerdocumentdetail.value
                    elif customerdocumentdetail.field.fieldtype==2:
                        idproofnumber = customerdocumentdetail.value
            except Exception as e:
                logger.info(e)
                customer_document_type = ''
                document_id=''
                customer_doc=''
                validity=''
                idproofnumber=''
            try:
                if request.session.get('address_verify_message') or request.session['status']:
                    message = request.session.get('address_verify_message')
                    status = request.session.get('status')
                    del request.session['address_verify_message']
                    del request.session['status']
            except Exception as e:
                logger.info(e)
                message=''
                status=''
            context = {
                'user_status' : user_status,
                'document_id':document_id,
                'customer_doc' : customer_doc if customer_doc else "",
                'message':message,
                'status':status,
                'additional_doc': Customerdocumentfiles.objects.filter(customerdocument=customer_doc, document_type="additionalPage"),
                'validity':validity if validity else "",
                'idproofnumber':idproofnumber if idproofnumber else ""
            }
            return render(request,'Idverification/idverification.html',context)
        else:
            return redirect('IdEdit')
    def post(self,request):
        return redirect('IdEdit')

@method_decorator(login_required, name='dispatch')
class IdEditView(View):
    template_name = 'Idverification/verification_form.html'
    def get(self,request):
        # documents = Documenttypes.objects.filter(filesrequired=3)
        validity_month=''
        validity_year=''
        customer_files_list = []
        customer_file_frontPage = ''
        customer_file_backPage = ''
        customer_file_selfiePage = ''
        customer_file_additionalPage = ''
        try:
            customer_doc = Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=1)
            customerdocumentdetails = Customerdocumentdetails.objects.filter(customerdocument=customer_doc)
            customer_files= Customerdocumentfiles.objects.filter(customerdocument=customer_doc)
            for customer_file in customer_files:
                customer_files_list.append(customer_file.filelocation)
                if customer_file.document_type == 'frontPage':
                    customer_file_frontPage = customer_file
                if customer_file.document_type == 'backPage':
                    customer_file_backPage = customer_file
                if customer_file.document_type == 'selfiePage':
                    customer_file_selfiePage = customer_file
                if customer_file.document_type == 'additionalPage':
                    customer_file_additionalPage = customer_file
                
            customer_document_type=customer_doc.documenttype.id
            for customerdocumentdetail in customerdocumentdetails:
                if customerdocumentdetail.field.fieldtype == 5:
                    validity = customerdocumentdetail.value
                    split = validity.split("-")
                    validity_year=split[1].strip()
                    validity_month=split[0].strip()
                elif customerdocumentdetail.field.fieldtype==2:
                    idproofnumber = customerdocumentdetail.value
        except Exception as e:
            logger.info(e)
            customer_file_additionalPage=''
            customer_file_selfiePage=''
            customer_file_backPage=''
            customer_file_frontPage=''
            customer_files_list=''
            customer_doc=''
            customerdocumentdetails = ''
            validity=''
            idproofnumber=''
            customer_document_type=''
            validity_year=''
            validity_month=''
        documents = Documenttypesforverification.objects.filter(verificationtype=1)
        document_list=[]
        for document in documents:
            document_list.append(document.documenttype)
        year = dt.today().year
        year_choices = list(range(year, year + 16, 1))
        months_choices = []
        for i in range(1,13):
            months_choices.append(datetime.date(2008, i, 1).strftime('%B'))
        context={
            'documenttypes' : document_list,
            'customer_document_type':customer_document_type,
            'validity_month' : validity_month if validity_month else "",
            'validity_year':int(validity_year) if validity_year else "",
            'idproofnumber':idproofnumber,
            'customer_doc':customer_doc,
            'months_choices':months_choices,
            'year_choices': year_choices,
            'customer_file_frontPage':customer_file_frontPage,
            'customer_file_backPage':customer_file_backPage,
            'customer_file_selfiePage':customer_file_selfiePage,
            'customer_file_additionalPage':customer_file_additionalPage
            
        }
        try:
            if request.session.get('address_verify_message') or request.session['status']:
                # context['message'] = request.session.get('address_verify_message')
                # context['status'] = request.session.get('status')
                del request.session['address_verify_message']
                del request.session['status']
        except Exception as e:
            logger.info(e)
            pass
        return render(request,'Idverification/verification_form.html',context)
    def post(self,request):
        
        def validation():
            if request.POST.get("check")=="Passport" or request.POST.get("check")=="Driving License":
                
                if not request.POST.get('docId'):
                  
                    return {
                    'status' : False,
                    'message' : 'please add id number',
                    }
                elif not request.POST.get('validityMonth') and not request.POST.get('validityYear'):
                   
                    return{
                        'status' : False,
                        'message' : 'please add validity year and month',
                    }
                
                elif not request.FILES.get('frontPage') or not request.FILES.get('backPage') or not request.FILES.get('selfiePage'):
                    # check here the customer already have files
                    try:
                        customer_doc=Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=request.POST.get('VerificationType'))
                        customer_files= Customerdocumentfiles.objects.filter(customerdocument=customer_doc)
                        if customer_files.exists():
                            if request.FILES.get('frontPage'):
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
                                elif not all(ord(c) < 128 for c in request.FILES.get('frontPage').name):
                                    return {
                                        'status' : False,
                                        'message' : 'Special characters should not be in file name',
                                        }
                                else:
                                    # customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='frontPage').update(
                                    #     filelocation=request.FILES.get('frontPage')
                                    # )
                                    customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='frontPage').first()
                                    customer_files.filelocation=request.FILES.get('frontPage')
                                    customer_files.save()

                            if request.FILES.get('backPage'):
                                ext = os.path.splitext(request.FILES.get('backPage').name)[1]
                                filesize = request.FILES.get('backPage').size
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
                                elif not all(ord(c) < 128 for c in request.FILES.get('backPage').name):
                                    return {
                                        'status' : False,
                                        'message' : 'Special characters should not be in file name',
                                        }
                                else:
                                    customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='backPage').first()
                                    customer_files.filelocation=request.FILES.get('backPage')
                                    customer_files.save()
                            if request.FILES.get('selfiePage'):
                                ext = os.path.splitext(request.FILES.get('selfiePage').name)[1]
                                filesize = request.FILES.get('selfiePage').size
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
                                elif not all(ord(c) < 128 for c in request.FILES.get('selfiePage').name):
                                    return {
                                        'status' : False,
                                        'message' : 'Special characters should not be in file name',
                                        }
                                else:
                                    customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='selfiePage').first()
                                    customer_files.filelocation=request.FILES.get('selfiePage')
                                    customer_files.save()
                            if request.FILES.get('additionalPage'):
                                ext = os.path.splitext(request.FILES.get('additionalPage').name)[1]
                                filesize = request.FILES.get('additionalPage').size
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
                                elif not all(ord(c) < 128 for c in request.FILES.get('additionalPage').name):
                                    return {
                                        'status' : False,
                                        'message' : 'Special characters should not be in file name',
                                        }
                                else:
                                    customer_files = Customerdocumentfiles.objects.filter(customerdocument=customer_doc,
                                                                                          document_type='additionalPage').first()
                                    if customer_files:                                                                                          
                                        customer_files.filelocation = request.FILES.get('additionalPage')
                                        customer_files.save()
                                    else:
                                        customer_files = Customerdocumentfiles.objects.create(
                                            customerdocument=customer_doc, filelocation=request.FILES.get('additionalPage'),
                                            document_type='additionalPage'
                                        )
                        else:
                            pass

                    except Exception as e:
                        logger.info(e)
                        pass
                    try:
                        customer_doc=Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=request.POST.get('VerificationType'))
                        customer_files= Customerdocumentfiles.objects.filter(customerdocument=customer_doc)
                       
                        if request.POST.get("check")=="Passport":
                            customer_document_details1 = Customerdocumentdetails.objects.get(
                                customerdocument=customer_doc, field = Documentfields.objects.get(fieldname="Passport Number")
                                )
                            customer_document_details1.value=request.POST.get('docId')
                            customer_document_details1.save()
                            customer_document_details2 = Customerdocumentdetails.objects.get(
                                customerdocument=customer_doc,
                                field = Documentfields.objects.get(fieldname="Validity")
                            )
                            months_array = []
                            for i in range(1,13):
                                months_array.append(datetime.date(2008, i, 1).strftime('%B'))
                            month = request.POST.get('validityMonth')
                            year = int(request.POST.get('validityYear'))
                            if dt.today().year == year:
                                current_monthinteger = dt.today().month - 1
                                if month in months_array:
                                    validity_month_index=months_array.index(month)
                                    if validity_month_index < current_monthinteger:
                                        return {
                                        'status' : False,
                                        'message' : 'Validity Expired',
                                        }
                                    else:
                                        customer_document_details2.value = str(request.POST.get('validityMonth'))+"-"+str(request.POST.get('validityYear'))# need changes here
                                        customer_document_details2.save()
                                        return{
                                                'status' : True,
                                                'message' : 'Updated successfully',
                                                
                                            }

                            else:
                                customer_document_details2.value = str(request.POST.get('validityMonth'))+"-"+str(request.POST.get('validityYear'))# need changes here
                                customer_document_details2.save()
                            
                        elif request.POST.get("check")=="Driving License":
                            customer_document_details1 = Customerdocumentdetails.objects.get(
                                customerdocument=customer_doc,
                                field = Documentfields.objects.get(fieldname="Driving License Number")
                            )
                            customer_document_details1.value = request.POST.get('docId')
                            customer_document_details1.save()
                            customer_document_details2 = Customerdocumentdetails.objects.get(
                                customerdocument=customer_doc,
                                field = Documentfields.objects.get(fieldname="Valid To")
                            )
                            months_array = []
                            for i in range(1,13):
                                months_array.append(datetime.date(2008, i, 1).strftime('%B'))
                            month = request.POST.get('validityMonth')
                            year = int(request.POST.get('validityYear'))
                            if dt.today().year == year:
                                current_monthinteger = dt.today().month - 1
                                if month in months_array:
                                    validity_month_index=months_array.index(month)
                                    if validity_month_index < current_monthinteger:
                                        return {
                                        'status' : False,
                                        'message' : 'Validity Expired',
                                        }
                                    else:
                                        customer_document_details2.value = str(request.POST.get('validityMonth'))+"-"+str(request.POST.get('validityYear'))# need changes here
                                        customer_document_details2.save()
                                        return{
                                                'status' : True,
                                                'message' : 'Updated successfully',
                                                
                                            }

                            else:
                                customer_document_details2.value = str(request.POST.get('validityMonth'))+"-"+str(request.POST.get('validityYear'))# need changes here
                                customer_document_details2.save()
                        return{
                            'status' : True,
                            'message' : 'Updated successfully',
                            
                        }
                    except Exception as e:
                        logger.info(e)
                        return{
                            'status' : False,
                            'message' : 'please choose all documents',
                            
                        }
                
                    
                else:
                    
                    months_array = []
                    for i in range(1,13):
                       months_array.append(datetime.date(2008, i, 1).strftime('%B'))
                    month = request.POST.get('validityMonth')
                    year = int(request.POST.get('validityYear'))
                    if dt.today().year == year:
                        current_monthinteger = dt.today().month - 1
                        if month in months_array:
                            validity_month_index=months_array.index(month)
                            if validity_month_index < current_monthinteger:
                                return {
                                'status' : False,
                                'message' : 'Validity Expired',
                                }
                    else:
                        pass
                    try:
                        filename1 = request.FILES.get('frontPage').name
                        filename2 = request.FILES.get('backPage').name
                        filename3 = request.FILES.get('selfiePage').name
                        ext1 = os.path.splitext(request.FILES.get('frontPage').name)[1]
                        ext2 = os.path.splitext(request.FILES.get('backPage').name)[1]
                        ext3 = os.path.splitext(request.FILES.get('selfiePage').name)[1]
                        filesize1 = request.FILES.get('frontPage').size
                        filesize2 = request.FILES.get('backPage').size
                        filesize3 = request.FILES.get('selfiePage').size
                        file_extensions = [ext1, ext2, ext3]
                        file_sizes = [filesize1, filesize2, filesize3]
                        file_names = [filename1, filename2, filename3]
                        if request.FILES.get('additionalPage'):
                            filename4 = request.FILES.get('additionalPage').name
                            ext4 = os.path.splitext(request.FILES.get('additionalPage').name)[1]
                            filesize4 = request.FILES.get('additionalPage').size
                            file_extensions.append(ext4)
                            file_sizes.append(filesize4)
                            file_names.append(filename4)
                        for ext in file_extensions:
                            if not ext in settings.ALLOWED_FORMATS:
                                return {
                                'status' : False,
                                'message' : 'Incorrect file format',
                                }
                        for filesize in file_sizes:
                            if filesize > settings.MAX_FILE_SIZE:
                                return {
                                    'status' : False,
                                    'message' : 'Maximum file size allowed is 10 MB',
                                    }
                        if not all(ord(ch) < 128  for filename in file_names for ch in filename):
                            return {
                                'status' : False,
                                'message' : 'Special characters should not be in file name',
                                } 
                    except Exception as e:
                        logger.info(e)
                        pass
                    try:
                        customer_doc=Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=request.POST.get('VerificationType'))
                        customer_files= Customerdocumentfiles.objects.filter(customerdocument=customer_doc)
                        if customer_files.exists():
                            if request.FILES.get('frontPage'):
                                customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='frontPage').update(
                                    filelocation=request.FILES.get('frontPage')
                                )
                            if request.FILES.get('backPage'):
                                customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='backPage').update(
                                    filelocation=request.FILES.get('backPage')
                                )
                            if request.FILES.get('selfiePage'):
                                customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='selfiePage').update(
                                    filelocation=request.FILES.get('selfiePage')
                                )
                            if request.FILES.get('additionalPage'):
                                customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='additionalPage').update(
                                    filelocation=request.FILES.get('additionalPage')
                                )
                        else:
                            pass

                    except Exception as e:
                        logger.info(e)
                        pass
                    try:
                        customer_doc=Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=request.POST.get('VerificationType'))
                        customer_files= Customerdocumentfiles.objects.filter(customerdocument=customer_doc)
                        customer_document_details=Customerdocumentdetails.objects.filter(customerdocument=customer_doc)
                        customer_doc.delete()
                        customer_files.delete()
                        customer_document_details.delete()
                    except Exception as e:
                        logger.info(e)
                        pass
                    customer_doc = Customerdocuments.objects.create(
                        customer=Customers.objects.get(user=request.user),verificationtype=Documenttypesforverification.objects.get(documenttype__id=request.POST.get('idProof'),verificationtype=1),
                        documenttype = Documenttypes.objects.get(id=int(request.POST.get('idProof')))
                        )
                    customer_files1 = Customerdocumentfiles.objects.create(
                        customerdocument=customer_doc,filelocation=request.FILES.get('frontPage'),
                        document_type='frontPage'
                    )
                    
                    customer_files2 = Customerdocumentfiles.objects.create(
                        customerdocument=customer_doc,filelocation=request.FILES.get('backPage'),
                        document_type='backPage'
                    )
                    customer_files3 = Customerdocumentfiles.objects.create(
                        customerdocument=customer_doc,filelocation=request.FILES.get('selfiePage'),
                        document_type='selfiePage'
                    )
                    if request.FILES.get('additionalPage'):
                        customer_files4 = Customerdocumentfiles.objects.create(
                            customerdocument=customer_doc, filelocation=request.FILES.get('additionalPage'),
                            document_type='additionalPage'
                        )
                    if request.POST.get("check")=="Passport":
                        customer_document_details1 = Customerdocumentdetails.objects.create(
                            customerdocument=customer_doc,value=request.POST.get('docId'),
                            field = Documentfields.objects.get(fieldname="Passport Number"),

                        )
                        customer_document_details2 = Customerdocumentdetails.objects.create(
                            customerdocument=customer_doc,value=str(request.POST.get('validityMonth'))+"-"+str(request.POST.get('validityYear')),
                            field = Documentfields.objects.get(fieldname="Validity")
                        )
                    elif request.POST.get("check")=="Driving License": 
                        customer_document_details1 = Customerdocumentdetails.objects.create(
                            customerdocument=customer_doc,value=request.POST.get('docId'),
                            field = Documentfields.objects.get(fieldname="Driving License Number")
                        )
                        customer_document_details2 = Customerdocumentdetails.objects.create(
                            customerdocument=customer_doc,value=str(request.POST.get('validityMonth'))+"-"+str(request.POST.get('validityYear')),
                            field = Documentfields.objects.get(fieldname="Valid To")
                        )
                    
                    return{
                        'status' : True,
                        'message' : 'Uploaded successfully',
                    }
            elif not request.POST.get("check")=="Passport" and not request.POST.get("check")=="Driving License" and not request.POST.get("check")=="ID Card" and not request.POST.get("check")=="Other":
                return{
                    'status' : False,
                    'message' : 'Please choose id type',
                }
            else:
                
                if not request.POST.get('docId'):
                    return {
                    'status' : False,
                    'message' : 'please add id number',
                    }
                elif not request.FILES.get('frontPage') or not request.FILES.get('backPage') or not request.FILES.get('selfiePage'):
                    # check here the customer already have files
                    try:
                        customer_doc=Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=request.POST.get('VerificationType'))
                        customer_files= Customerdocumentfiles.objects.filter(customerdocument=customer_doc)
                        if customer_files.exists():
                            if request.FILES.get('frontPage'):
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
                                elif not all(ord(c) < 128 for c in request.FILES.get('frontPage').name):
                                    return {
                                        'status' : False,
                                        'message' : 'Special characters should not be in file name',
                                        }
                                else:
                                    customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='frontPage').first()
                                    customer_files.filelocation=request.FILES.get('frontPage')
                                    customer_files.save()
                            if request.FILES.get('backPage'):
                                ext = os.path.splitext(request.FILES.get('backPage').name)[1]
                                filesize = request.FILES.get('backPage').size
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
                                elif not all(ord(c) < 128 for c in request.FILES.get('backPage').name):
                                    return {
                                        'status' : False,
                                        'message' : 'Special characters should not be in file name',
                                        }
                                else:

                                    customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='backPage').first()
                                    customer_files.filelocation=request.FILES.get('backPage')
                                    customer_files.save()
                            if request.FILES.get('selfiePage'):
                                ext = os.path.splitext(request.FILES.get('selfiePage').name)[1]
                                filesize = request.FILES.get('selfiePage').size
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
                                elif not all(ord(c) < 128 for c in request.FILES.get('selfiePage').name):
                                    return {
                                        'status' : False,
                                        'message' : 'Special characters should not be in file name',
                                        }
                                else:

                                    customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='selfiePage').first()
                                    customer_files.filelocation=request.FILES.get('selfiePage')
                                    customer_files.save()
                            if request.FILES.get('additionalPage'):
                                ext = os.path.splitext(request.FILES.get('additionalPage').name)[1]
                                filesize = request.FILES.get('additionalPage').size
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
                                elif not all(ord(c) < 128 for c in request.FILES.get('additionalPage').name):
                                    return {
                                        'status' : False,
                                        'message' : 'Special characters should not be in file name',
                                        }
                                else:

                                    customer_files = Customerdocumentfiles.objects.filter(customerdocument=customer_doc,
                                                                                          document_type='additionalPage').first()
                                    if customer_files:
                                        customer_files.filelocation = request.FILES.get('additionalPage')
                                        customer_files.save()
                                    else:
                                        customer_files = Customerdocumentfiles.objects.create(
                                            customerdocument=customer_doc,
                                            filelocation=request.FILES.get('additionalPage'),
                                            document_type='additionalPage'
                                        )
                                    
                        else:
                            pass

                    except Exception as e:
                        logger.info(e)
                        pass
                    try:
                        customer_doc=Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=request.POST.get('VerificationType'))

                        if request.POST.get("check")=="ID Card":
                            customer_document_details = Customerdocumentdetails.objects.get(
                                customerdocument=customer_doc,
                                field = Documentfields.objects.get(fieldname="ID Card Number")
                            )
                            customer_document_details.value = request.POST.get('docId')
                            customer_document_details.save()
                        elif request.POST.get("check")=="Other": 
                            customer_document_details = Customerdocumentdetails.objects.get(
                                customerdocument=customer_doc,
                                field = Documentfields.objects.get(fieldname="ID Proof Number")
                            )
                            customer_document_details.value = request.POST.get('docId')
                            customer_document_details.save()
                        return{
                            'status' : True,
                            'message' : 'Updated successfully',
                        }
                        
                        
                    except Exception as e:
                        logger.info(e)
                        return{
                            'status' : False,
                            'message' : 'please choose all documents',
                            
                        }
                
                else:
                    try:
                        filename1 = request.FILES.get('frontPage').name
                        filename2 = request.FILES.get('backPage').name
                        filename3 = request.FILES.get('selfiePage').name
                        ext1 = os.path.splitext(request.FILES.get('frontPage').name)[1]
                        ext2 = os.path.splitext(request.FILES.get('backPage').name)[1]
                        ext3 = os.path.splitext(request.FILES.get('selfiePage').name)[1]
                        filesize1 = request.FILES.get('frontPage').size
                        filesize2 = request.FILES.get('backPage').size
                        filesize3 = request.FILES.get('selfiePage').size
                        file_extensions = [ext1, ext2, ext3]
                        file_sizes = [filesize1, filesize2, filesize3]
                        file_names = [filename1, filename2, filename3]
                        if request.FILES.get('additionalPage'):
                            filename4 = request.FILES.get('additionalPage').name
                            ext4 = os.path.splitext(request.FILES.get('additionalPage').name)[1]
                            filesize4 = request.FILES.get('additionalPage').size
                            file_extensions.append(ext4)
                            file_sizes.append(filesize4)
                            file_names.append(filename4)
                        for ext in file_extensions:
                            if not ext in settings.ALLOWED_FORMATS:
                                return {
                                    'status': False,
                                    'message': 'Incorrect file format',
                                }
                        for filesize in file_sizes:
                            if filesize > settings.MAX_FILE_SIZE:
                                return {
                                    'status': False,
                                    'message': 'Maximum file size allowed is 10 MB',
                                }
                        if not all(ord(ch) < 128 for filename in file_names for ch in filename):
                            return {
                                'status': False,
                                'message': 'Special characters should not be in file name',
                            }
                    except Exception as e:
                        logger.info(e)
                        pass
                    try:
                        customer_doc=Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=request.POST.get('VerificationType'))
                        customer_files= Customerdocumentfiles.objects.filter(customerdocument=customer_doc)
                        if customer_files.exists():
                            if request.FILES.get('frontPage'):
                                customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='frontPage').update(
                                    filelocation=request.FILES.get('frontPage')
                                )
                            if request.FILES.get('backPage'):
                                customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='backPage').update(
                                    filelocation=request.FILES.get('backPage')
                                )
                            if request.FILES.get('selfiePage'):
                                customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='selfiePage').update(
                                    filelocation=request.FILES.get('selfiePage')
                                )
                            if request.FILES.get('additionalPage'):
                                customer_files=Customerdocumentfiles.objects.filter(customerdocument=customer_doc,document_type='additionalPage').update(
                                    filelocation=request.FILES.get('additionalPage')
                                )
                        else:
                            pass

                    except Exception as e:
                        logger.info(e)
                        pass
                    try:
                        customer_doc=Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=request.POST.get('VerificationType'))
                        customer_files= Customerdocumentfiles.objects.filter(customerdocument=customer_doc)
                        customer_document_details=Customerdocumentdetails.objects.filter(customerdocument=customer_doc)
                        customer_doc.delete()
                        customer_files.delete()
                        customer_document_details.delete()
                    except Exception as e:
                        logger.info(e)
                        pass
                    customer_doc = Customerdocuments.objects.create(
                        customer=Customers.objects.get(user=request.user),verificationtype=Documenttypesforverification.objects.get(documenttype__id=request.POST.get('idProof'),verificationtype=1),
                        documenttype = Documenttypes.objects.get(id=int(request.POST.get('idProof')))
                        )
                    customer_files1 = Customerdocumentfiles.objects.create(
                        customerdocument=customer_doc,filelocation=request.FILES.get('frontPage'),
                        document_type='frontPage'
                    )
                    
                    customer_files2 = Customerdocumentfiles.objects.create(
                        customerdocument=customer_doc,filelocation=request.FILES.get('backPage'),
                        document_type='backPage'
                    )
                    customer_files3 = Customerdocumentfiles.objects.create(
                        customerdocument=customer_doc,filelocation=request.FILES.get('selfiePage'),
                        document_type='selfiePage'
                    )
                    if request.FILES.get('additionalPage'):
                        customer_files3 = Customerdocumentfiles.objects.create(
                            customerdocument=customer_doc, filelocation=request.FILES.get('additionalPage'),
                            document_type='additionalPage'
                        )
                    if request.POST.get("check")=="ID Card":
                        customer_document_details = Customerdocumentdetails.objects.create(
                            customerdocument=customer_doc,value=request.POST.get('docId'),
                            field = Documentfields.objects.get(fieldname="ID Card Number")
                        )
                    else: 
                        customer_document_details = Customerdocumentdetails.objects.create(
                            customerdocument=customer_doc,value=request.POST.get('docId'),
                            field = Documentfields.objects.get(fieldname="ID Proof Number")
                        )
                    return{
                        'status' : True,
                        'message' : 'Uploaded successfully',
                    }
           
        response = validation()
        documents = Documenttypesforverification.objects.filter(verificationtype=1)
        document_list=[]
        year = dt.today().year
        year_choices = list(range(year, year + 16, 1))
        months_choices = []
        for i in range(1,13):
            months_choices.append(datetime.date(2008, i, 1).strftime('%B'))
        for document in documents:
            document_list.append(document.documenttype)
        try:
            customer_doc = Customerdocuments.objects.get(customer__user=request.user,verificationtype__verificationtype=1)
            customerdocumentdetails = Customerdocumentdetails.objects.filter(customerdocument=customer_doc)
            customer_files= Customerdocumentfiles.objects.filter(customerdocument=customer_doc)
            for customer_file in customer_files:
                if customer_file.document_type == 'frontPage':
                    customer_file_frontPage = customer_file
                if customer_file.document_type == 'backPage':
                    customer_file_backPage = customer_file
                if customer_file.document_type == 'selfiePage':
                    customer_file_selfiePage = customer_file
                if customer_file.document_type == 'additionalPage':
                    customer_file_additionalPage = customer_file
        except Exception as e:
            logger.info(e)
            customer_doc=''
            customer_file_frontPage=''
            customer_file_backPage=''
            customer_file_selfiePage=''
            customer_file_additionalPage=''
        if response and not response.get('status'):
            if request.POST.get('page') == '2':
                if request.session.get('idDetails'):
                    del request.session['idDetails']
                if request.session.get('idErrorMsg'):
                    del request.session['idErrorMsg']
                request.session['idErrorMsg'] = response.get('message')
                request.session['idDetails'] = request.POST.dict()
                return redirect('/pageStatus/?page=2')
            request.session['address_verify_message'] = response.get('message')
            prev= request.POST.dict()
            prev_files = request.FILES.dict()
           
            try:
                prev['validityYear'] = int(prev['validityYear'])
            except Exception as e:
                logger.info(e)
                pass
            context={
                'message' : response.get('message'),
                'status' : False,
                'documenttypes' : document_list,
                'months_choices':months_choices,
                'year_choices': year_choices,
                'prev':prev,
                'prev_id':int(prev['idProof']),
                customer_doc:'customer_doc',
                'customer_file_frontPage':customer_file_frontPage,
                'customer_file_backPage':customer_file_backPage,
                'customer_file_selfiePage':customer_file_selfiePage,

                
              
            }
            return render(request, 'Idverification/verification_form.html',context)
        else:
            if request.POST.get('page') == '2':
                return redirect('/pageStatus/?page=3')
            request.session['address_verify_message'] = response.get('message')
            request.session['status'] = True
            return redirect('idList')