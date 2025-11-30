from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse,HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.http.multipartparser import MultiPartParser
from django.db import IntegrityError
from .serializers import MenuSerializer, UserSerializer, validate_img
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from rest_framework import serializers
from .models import Menuu, Userss, Orderss
from datetime import datetime, timedelta
import cloudinary.uploader
from .auth_check import admin_required, login_required
import json
import bcrypt
import jwt
import time
import traceback
import uuid             #Orders
from django.utils.html import escape
from django.conf import settings
from django.db.models import Q                          #used in Django to write OR, AND, and complex filters inside your database queries.
from django.core.mail import send_mail, EmailMessage
# from django.core.mail import send_mail as django_send_mail, EmailMessage
#Fix email sending (avoid name collision & reveal backend errors)
SECRETKEY= settings.SECRET_KEY



# @login_required
# def get_dish(req):
#     all_items = Menu.objects.all()
#     return render(req, 'menu.html', {'menu': all_items})

# @login_required
# def get_dish(req):
#     # fetch items
#     all_items = Menuu.objects.all()

#     # read payload attached by your login_required decorator (if any)
#     payload = getattr(req, 'user_payload', None) or {}
#     role = payload.get('role', '')
#     userid = payload.get('userid', None)

#     # DEBUG: uncomment to print to console while testing
#     # print("get_dish payload:", payload)

#     return render(req, 'menu.html', {
#         'menu': all_items,
#         'role': role,
#         'logged_in_userid': userid,
#     })



# @login_required
# def get_dish(req):
#     try:
#         items = Menuu.objects.all()
#         serializer = MenuSerializer(items, many=True)
#         return JsonResponse({"menu": serializer.data}, status=200)
#     except Exception as e:
#         traceback.print_exc()
#         return JsonResponse({"error": str(e)}, status=500)



# from django.http import JsonResponse
# from django.contrib.auth.decorators import login_required
# from .models import Menuu
# from .serializers import MenuSerializer
# import traceback

# @login_required
def get_dish(req):
    try:
        # -----------------------------
        # GET QUERY PARAMS
        # -----------------------------
        category = req.GET.get("category")            # /menu?category=veg
        max_price = req.GET.get("max_price")          # /menu?max_price=200
        min_price = req.GET.get("min_price")          # /menu?min_price=50
        search = req.GET.get("search")                # /menu?search=chicken

        # -----------------------------
        # FILTER DATA
        # -----------------------------
        items = Menuu.objects.all()

        if category:
            items = items.filter(Category__iexact=category)

        if min_price:
            items = items.filter(Price__gte=min_price)

        if max_price:
            items = items.filter(Price__lte=max_price)

        if search:
            items = items.filter(DishName__icontains=search)

        # -----------------------------
        # SERIALIZE AND RETURN
        # -----------------------------
        serializer = MenuSerializer(items, many=True)
        return JsonResponse({"menu": serializer.data}, status=200)

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
    



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

    

# @login_required
# @admin_required
# def get_users(req):
#     users_data = list(Userss.objects.all().values())

#     payload = req.user_payload  # from decorator
#     logged_id = payload.get("userid")
#     role = payload.get("role")

#     return JsonResponse({"all_users":users_data})

#     '''for templates'''
#     # return render(req, 'show_userss.html', {
#     #     'users': users_data,
#     #     'logged_in_userid': logged_id,
#     #     'role': role
#     # })

@login_required
@admin_required
def get_users(req):
    try:
        # -----------------------------------------
        # QUERY PARAMS
        # -----------------------------------------
        role_filter = req.GET.get("role")           # /get_users?role=Admin
        search = req.GET.get("search")              # /get_users?search=balaji

        page = int(req.GET.get("page", 1))          # default 1
        limit = int(req.GET.get("limit", 10))       # default 10
        offset = (page - 1) * limit

        # -----------------------------------------
        # FETCH BASE QUERY
        # -----------------------------------------
        users = Userss.objects.all()

        # -----------------------------------------
        # FILTER BY ROLE
        # -----------------------------------------
        if role_filter:
            users = users.filter(Role__iexact=role_filter)

        # -----------------------------------------
        # SEARCH (username or email)
        # -----------------------------------------
        if search:
            users = users.filter(
                Q(Username__icontains=search) |
                Q(Email__icontains=search)
            )

        total_count = users.count()

        # -----------------------------------------
        # PAGINATION
        # -----------------------------------------
        users = users[offset: offset + limit]

        # Convert queryset to list of dictionaries
        users_data = list(users.values())

        return JsonResponse({
            "total": total_count,
            "page": page,
            "limit": limit,
            "results": users_data
        }, status=200)

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)



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

        if not bcrypt.checkpw(pw.encode('utf-8'), user.Password.encode('utf-8')):
            return JsonResponse({'msg': 'Wrong userid or password'}, status=401)

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
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        # IMPORTANT: return JSON, no redirect
        response = JsonResponse({
            "success": True,
            "msg": "Login successful",
            "role": user.Role,
            "userid": user.Userid
        })

        # FINAL cookie for Render + React
        response.set_cookie(
            key="my_cookie",
            value=token,
            httponly=True,
            samesite="None",
            secure=True,
            path="/",
            max_age=1800,
        )

        return response

    except Exception as e:
        print("Exception in login:", e)
        traceback.print_exc()
        return JsonResponse({"error": "Unexpected server error", "details": str(e)}, status=500)



# return JsonResponse({"success": True})
        # response.set_cookie(
        #     key='my_cookie',
        #     value=token,
        #     httponly=True,   # True is preferred; browser still sends cookie
        #     samesite='Lax',  # works for POST->redirect
        #     secure=False,    # MUST be False for http://127.0.0.1:8000
        #     path='/',
        #     max_age=1800,
        # )



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
    

#Orders

@login_required
@csrf_exempt
def add_to_cart(req, id):
    cart = req.session.get("cart", [])
    cart.append(id)
    req.session["cart"] = cart
    return JsonResponse({"msg": "Item added to cart"})


@login_required
def get_cart(req):
    cart = req.session.get("cart", [])
    dishes = Menuu.objects.filter(DishId__in=cart)
    data = list(dishes.values())
    return JsonResponse({"cart_items": data})


@login_required
@csrf_exempt
def place_order(req):
    cart = req.session.get("cart", [])
    if not cart:
        return JsonResponse({"error": "Cart is empty"}, status=400)

    dishes = Menuu.objects.filter(DishId__in=cart)
    total = sum(int(d.Price) for d in dishes)

    order_id = "ORD" + uuid.uuid4().hex[:8]
    delivery_time = datetime.now() + timedelta(minutes=30)

    order = Orderss.objects.create(
        OrderId=order_id,
        Userid=Userss.objects.get(Userid=req.user_payload["userid"]),
        Items=list(dishes.values()),
        TotalPrice=total,
        ExpectedDelivery=delivery_time
    )

    req.session["cart"] = []   # clear cart

    return JsonResponse({
        "msg": "Order Placed Successfully",
        "order_id": order.OrderId,
        "total_price": total,
        "expected_delivery": delivery_time.strftime("%I:%M %p"),
    })



def root_ok(request):
    return JsonResponse({"ok": True, "service": "rms"}, status=200)