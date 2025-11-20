from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse,HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.http.multipartparser import MultiPartParser
from django.db import IntegrityError
from .serializers import MenuSerializer, UserSerializer, validate_img
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from rest_framework import serializers
from .models import Menuu, Userss
from datetime import datetime, timedelta
import cloudinary.uploader
from .auth_check import admin_required, login_required
import json
import bcrypt
import jwt
import time
import traceback
from django.utils.html import escape
from django.conf import settings
SECRETKEY= settings.SECRET_KEY
from django.core.mail import send_mail, EmailMessage
# from django.core.mail import send_mail as django_send_mail, EmailMessage
#Fix email sending (avoid name collision & reveal backend errors)




# @login_required
# def get_dish(req):
#     all_items = Menu.objects.all()
#     return render(req, 'menu.html', {'menu': all_items})

@login_required
def get_dish(req):
    # fetch items
    all_items = Menuu.objects.all()

    # read payload attached by your login_required decorator (if any)
    payload = getattr(req, 'user_payload', None) or {}
    role = payload.get('role', '')
    userid = payload.get('userid', None)

    # DEBUG: uncomment to print to console while testing
    # print("get_dish payload:", payload)

    return render(req, 'menu.html', {
        'menu': all_items,
        'role': role,
        'logged_in_userid': userid,
    })




@csrf_exempt
@admin_required
def add_dish(req):
    # Only POST for AJAX form submissions from menu.html
    if req.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    # Expect multipart/form-data
    content_type = req.META.get('CONTENT_TYPE', '')
    if 'multipart/form-data' not in content_type:
        return JsonResponse({'error': 'Expected multipart/form-data'}, status=400)

    # Parse multipart (works even if no file)
    upload_handlers = [TemporaryFileUploadHandler(req)]
    parser = MultiPartParser(req.META, req, upload_handlers=upload_handlers)
    data, files = parser.parse()

    # Read fields (DishId expected because you want manual id)
    payload = {
        'DishId': data.get('DishId'),
        'DishName': data.get('DishName'),
        'Ingredients': data.get('Ingredients'),
        'Price': data.get('Price'),
        'Category': data.get('Category'),
    }

    # Handle optional image
    pic = files.get('Image')
    if pic:
        try:
            # optional: validate_img(pic) if you have that function
            upload_result = cloudinary.uploader.upload(pic)
            payload['Image'] = upload_result.get('secure_url')
        except Exception as e:
            return JsonResponse({'Image': [f'Image upload failed: {str(e)}']}, status=400)
    else:
        # If your serializer requires Image, you can leave it out and serializer will complain.
        # Otherwise set a default empty string or default image url:
        # payload['Image'] = ''
        pass

    # Validate via serializer (returns field-specific errors)
    serializer = MenuSerializer(data=payload)
    if serializer.is_valid():
        serializer.save()
        return JsonResponse({'Message': 'Dish added Successfully'}, status=201)
    else:
        # return serializer.errors directly (frontend will display them)
        # serializer.errors is a dict like {'DishId':['This field is required.']}
        return JsonResponse(serializer.errors, status=400)




@csrf_exempt
@admin_required
def update_dish(req, id):
    try:
        menu = Menuu.objects.get(DishId=id)
    except Menuu.DoesNotExist:
        return JsonResponse({'Error': 'Dish Not Found'}, status=404)

    if req.method not in ['PUT', 'PATCH']:
        return JsonResponse({'Error': 'Only PUT/PATCH methods are allowed'}, status=405)

    # Check if multipart form data
    content_type = req.META.get('CONTENT_TYPE', '')
    if 'multipart/form-data' in content_type:
        upload_handlers = [TemporaryFileUploadHandler(req)]
        parser = MultiPartParser(req.META, req, upload_handlers=upload_handlers)
        data, files = parser.parse()
    else:
        return JsonResponse({'Error': 'Expected multipart form data'}, status=400)

    # Get fields
    name = data.get('DishName')
    ingre = data.get('Ingredients')
    price = data.get('Price')
    cat = data.get('Category')
    pic = files.get('Image')

    # Update fields if provided
    if name:
        menu.DishName = name
    if ingre:
        menu.Ingredients = ingre
    if price:
        menu.Price = price
    if cat:
        menu.Category = cat

    # Handle image if provided
    if pic:
        # Validate size
        max_size = 2 * 1024 * 1024
        if pic.size > max_size:
            return JsonResponse({'Error': 'Image size should not exceed 2MB'}, status=400)
        # Validate type
        allowed_types = ['image/jpeg', 'image/png']
        if pic.content_type not in allowed_types:
            return JsonResponse({'Error': 'Only JPEG and PNG images are allowed'}, status=400)
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(pic)
        menu.Image = upload_result.get('secure_url')

    # Save updated dish
    menu.save()
    return JsonResponse({'Message': 'Menu successfully updated'})
   


@csrf_exempt
@admin_required
def del_dish(req,id):
    try:
        menu = Menuu.objects.get(DishId=id)
    
    except Menuu.DoesNotExist:
        return JsonResponse({"error":'ID not found'},status=404)
    
    menu.delete()
    return JsonResponse({'msg':'Item deleted Successfully'})

    

@login_required
@admin_required
def get_users(req):
    users_data = list(Userss.objects.all().values())

    payload = req.user_payload  # from decorator
    logged_id = payload.get("userid")
    role = payload.get("role")

    return render(req, 'show_userss.html', {
        'users': users_data,
        'logged_in_userid': logged_id,
        'role': role
    })



@csrf_exempt
def reg_user(req):
    if req.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    try:
        id = req.POST.get('Userid')
        name = req.POST.get('Username')
        email = req.POST.get('Email')
        pw = req.POST.get('Password')

        if not all([id, name, email, pw]):
            return JsonResponse({'error': 'All fields are required'}, status=400)

        # if Userid is integer in your model convert it, else keep as string
        try:
            id_val = int(id)
        except Exception:
            id_val = id

        encrypted_password = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt(14)).decode('utf-8')

        # IGNORE any Role sent by frontend
        _ = req.POST.get('Role')

        # CORRECT: check the actual model field name (Role) case-insensitively
        admin_exists = Userss.objects.filter(Role__iexact='admin').exists()

        # If no admin exists → make this user admin
        user_role = 'Admin' if not admin_exists else 'User'

        new_user = Userss.objects.create(
            Userid=id_val,
            Username=name,
            Email=email,
            Password=encrypted_password,
            Role=user_role
        )

        # send_mail(subject, message, from_email, recipient_list)
        try:
            send_mail(          #django_
                "Welcome to my Restaurant!!!",
                f"Thank you {new_user.Username} for registering in my Restaurants App!!! We are waiting for your order !!!",
                settings.EMAIL_HOST_USER,
                [new_user.Email],
                fail_silently=False,   # set False during dev so errors are raised / logged
            )
        except Exception as mail_err:
            print("django_send_mail failed:", repr(mail_err))


        return JsonResponse({
            'msg': 'User Successfully Created',
            'data': {
                'Userid': new_user.Userid,
                'Username': new_user.Username,
                'role': new_user.Role
            }
        }, status=201)

    except IntegrityError:
        return JsonResponse({'error': 'User with this ID or email already exists'}, status=400)

    except Exception as e:
        print("reg_user exception:", repr(e))  # dev: print full exception
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)



@csrf_exempt
def login(req):
    try:
        if req.method != 'POST':
            return JsonResponse({'error': 'Only POST allowed'}, status=405)

        id = req.POST.get('Userid')
        pw = req.POST.get('Password')

        if not all([id, pw]):
            return JsonResponse({'error': 'Userid and Password required'}, status=400)

        try:
            user = Userss.objects.get(Userid=id)
        except Userss.DoesNotExist:
            return JsonResponse({'error': 'User Not Found'}, status=404)

        # check password
        if not bcrypt.checkpw(pw.encode('utf-8'), user.Password.encode('utf-8')):
            return JsonResponse({'msg': 'Wrong userid or password'}, status=401)

        # Build JWT using datetime objects (PyJWT will handle them)
        now = datetime.utcnow()
        exp_time = now + timedelta(minutes=30)

        payload = {
            'userid': user.Userid,
            'username': user.Username,
            'role': user.Role,
            'iat': now,
            'exp': exp_time
        }

        token = jwt.encode(payload, SECRETKEY, algorithm='HS256')
        # PyJWT v1 returns bytes; v2 returns string — normalize to str
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        # Return a redirect and set cookie
        # response = redirect('/home/')
        return JsonResponse({"success": True})
        response.set_cookie(
            key='my_cookie',
            value=token,
            httponly=True,   # True is preferred; browser still sends cookie
            samesite='Lax',  # works for POST->redirect
            secure=False,    # MUST be False for http://127.0.0.1:8000
            path='/',
            max_age=1800,
        )

        print("Issued JWT exp:", exp_time.isoformat())
        print("COOKIE SET:", response.cookies)  # debug print
        return response

    except jwt.ExpiredSignatureError:
        # Shouldn't happen while creating token, but keep explicit
        return JsonResponse({'error': 'Token creation error: expired signature'}, status=500)

    except Exception as e:
        # print full traceback to server console for debugging and return JSON error
        print("Exception in login view:", repr(e))
        traceback.print_exc()
        return JsonResponse({'error': 'Unexpected server error in login', 'details': str(e)}, status=500)




@login_required
def whoami(req):
    payload = req.user_payload  # comes from login_required decorator
    return JsonResponse({
        'userid': payload.get('userid'),
        'username': payload.get('username'),
        'role': payload.get('role')
    })



@csrf_exempt
def update_user(req, id):
    if req.method not in ['PUT', 'PATCH']:
        return JsonResponse({'error': 'Only PUT/PATCH allowed'}, status=405)

    try:
        user = Userss.objects.get(Userid=id)
    except Userss.DoesNotExist:
        return JsonResponse({'error': 'User Not Found'}, status=404)

    # Parse multipart form-data manually
    content_type = req.META.get('CONTENT_TYPE', '')
    if 'multipart/form-data' in content_type:
        upload_handlers = [TemporaryFileUploadHandler(req)]
        parser = MultiPartParser(req.META, req, upload_handlers=upload_handlers)
        data, files = parser.parse()
    else:
        return JsonResponse({'error': 'Expected multipart/form-data'}, status=400)

    # Get updated fields
    name = data.get('Username')
    email = data.get('Email')
    pw = data.get('Password')

    if name:
        user.Username = name
    if email:
        user.Email = email
    if pw:
        user.Password = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt(14)).decode('utf-8')

    try:
        user.save()
        return JsonResponse({
            'msg': 'User successfully updated',
            'data': {
                'Userid': user.Userid,
                'Username': user.Username,
                'Email': user.Email
            }
        })
    except IntegrityError:
        return JsonResponse({'error': 'Email already in use'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)
    

@csrf_exempt
@login_required
def modify_my_details(request):
    if request.method not in ["POST", "PUT", "PATCH"]:
        return JsonResponse({"error": "Only POST/PUT/PATCH allowed"}, status=405)

    payload = request.user_payload
    user_id = payload.get("userid")

    try:
        user = Userss.objects.get(Userid=user_id)
    except Userss.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    data = request.POST
    name = data.get("Username")
    email = data.get("Email")
    pw = data.get("Password")

    if name:
        user.Username = name
    if email:
        user.Email = email
    if pw:
        user.Password = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(14)).decode("utf-8")

    try:
        user.save()
        return JsonResponse({"msg": "Your details were updated successfully"})
    except IntegrityError:
        return JsonResponse({"error": "Email already in use"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)




@csrf_exempt
@admin_required
def promote_user(req, id):
    if req.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    try:
        user = Userss.objects.get(Userid=id)
        user.Role = 'Admin'
        user.save()
        return JsonResponse({'msg': f'{id} promoted to admin'})
    except Userss.DoesNotExist:
        return JsonResponse({'error': 'User Not Found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)



@csrf_exempt
def del_user(req, id):
    if req.method != 'DELETE':
        return JsonResponse({'error': 'Only DELETE allowed'}, status=405)

    try:
        user = Userss.objects.get(Userid=id)
    except Userss.DoesNotExist:
        return JsonResponse({'error': 'User Not Found'}, status=404)

    try:
        user.delete()
        return JsonResponse({'msg': f'User {id} deleted successfully'})
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)