from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse,HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.http.multipartparser import MultiPartParser
from django.db import IntegrityError
from .serializers import MenuSerializer, UserSerializer, validate_img
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from rest_framework import serializers
from .models import Menuu, Userss, Orderss, CartItem
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
import stripe
from django.views.decorators.http import require_POST
from rest_framework import status
from .services import recommend_food_by_mood

# from rest_framework.decorators import api_view
# from rest_framework.response import Response

# from django.core.mail import send_mail as django_send_mail, EmailMessage
#Fix email sending (avoid name collision & reveal backend errors)
SECRETKEY= settings.SECRET_KEY
stripe.api_key = settings.STRIPE_SECRET_KEY



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

@login_required
def get_user(request, id):
    if request.method != "GET":
        return JsonResponse({"error": "GET only"}, status=405)

    try:
        user = Userss.objects.get(Userid=id)
    except Userss.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    return JsonResponse({
        "Userid": user.Userid,
        "Username": user.Username,
        "Email": user.Email
    })


@csrf_exempt
def reg_user(req):
    if req.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    try:
        name = req.POST.get('Username')
        email = req.POST.get('Email')
        pw = req.POST.get('Password')

        if not all([name, email, pw]):
            return JsonResponse({'error': 'All fields are required'}, status=400)

        # if Userid is integer in your model convert it, else keep as string
        # try:
        #     id_val = int(id)
        # except Exception:
        #     id_val = id

        encrypted_password = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt(14)).decode('utf-8')

        # IGNORE any Role sent by frontend
        _ = req.POST.get('Role')

        # CORRECT: check the actual model field name (Role) case-insensitively
        admin_exists = Userss.objects.filter(Role__iexact='admin').exists()

        # If no admin exists → make this user admin
        user_role = 'Admin' if not admin_exists else 'User'

        new_user = Userss.objects.create(
            # Userid=id_val,
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

        # id = req.POST.get('Userid')
        email = req.POST.get('Email')
        pw = req.POST.get('Password')

        if not all([email, pw]):
            return JsonResponse({'error': 'Email and Password required'}, status=400)

        try:
            user = Userss.objects.get(Email=email)
        except Userss.DoesNotExist:
            return JsonResponse({'error': 'User Not Found'}, status=404)

        if not bcrypt.checkpw(pw.encode('utf-8'), user.Password.encode('utf-8')):
            return JsonResponse({'msg': 'Wrong Email or password'}, status=401)

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
            "Email": user.Email
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



@csrf_exempt
@login_required
def whoami(request):
    payload = request.user_payload
    user_id = payload.get("userid")

    try:
        user = Userss.objects.get(Userid=user_id)
        return JsonResponse({
            "userid": user.Userid,
            "username": user.Username,  # fresh from DB
            "email": user.Email,
            "role": user.Role
        })
    except Userss.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)



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
    

# @csrf_exempt
# @login_required
# def modify_my_details(request):
#     if request.method not in ["POST", "PUT", "PATCH"]:
#         return JsonResponse({"error": "Only POST/PUT/PATCH allowed"}, status=405)

#     payload = request.user_payload
#     user_id = payload.get("userid")

#     try:
#         user = Userss.objects.get(Userid=user_id)
#     except Userss.DoesNotExist:
#         return JsonResponse({"error": "User not found"}, status=404)

#     data = request.POST
#     name = data.get("Username")
#     email = data.get("Email")
#     pw = data.get("Password")

#     if name:
#         user.Username = name
#     if email:
#         user.Email = email
#     if pw:
#         user.Password = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(14)).decode("utf-8")

#     try:
#         user.save()
#         return JsonResponse({"msg": "Your details were updated successfully"})
#     except IntegrityError:
#         return JsonResponse({"error": "Email already in use"}, status=400)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)


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
        # Return the updated user data along with the success message
        return JsonResponse({
            "msg": "Your details were updated successfully",
            "user": {
                "userid": user.Userid,
                "username": user.Username,
                "email": user.Email,
                "role": user.Role
            }
        })
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

# @login_required
# @csrf_exempt
# def add_to_cart(req, id):
#     cart = req.session.get("cart", [])
#     cart.append(id)
#     req.session["cart"] = cart
#     print("ADD_TO_CART session cart:", req.session.get("cart"))  # DEBUG
#     return JsonResponse({"msg": "Item added to cart"})


# @login_required
# def get_cart(req):
#     cart = req.session.get("cart", [])
#     dishes = Menuu.objects.filter(DishId__in=cart)
#     data = list(dishes.values())
#     return JsonResponse({"cart_items": data})

# Orders

# @login_required
# @csrf_exempt
# def add_to_cart(req, id):
#     try:
#         id_int = int(id)
#     except ValueError:
#         return JsonResponse({"error": "Invalid dish id"}, status=400)

#     # Optional: ensure dish exists
#     if not Menuu.objects.filter(DishId=id_int).exists():
#         return JsonResponse({"error": "Dish not found"}, status=404)

#     cart = req.session.get("cart", [])

#     # normalize existing stored ids to int
#     normalized_cart = []
#     for v in cart:
#         try:
#             normalized_cart.append(int(v))
#         except Exception:
#             continue

#     if id_int not in normalized_cart:
#         normalized_cart.append(id_int)

#     req.session["cart"] = normalized_cart
#     print("ADD_TO_CART session cart:", req.session.get("cart"))  # DEBUG

#     return JsonResponse({"msg": "Item added to cart"})


# @login_required
# def get_cart(req):
#     cart = req.session.get("cart", [])
#     print("GET_CART raw session cart:", cart)  # DEBUG

#     ids = []
#     for v in cart:
#         try:
#             ids.append(int(v))
#         except Exception:
#             continue

#     if not ids:
#         return JsonResponse({"cart_items": []})

#     dishes = Menuu.objects.filter(DishId__in=ids)
#     print("GET_CART dishes count:", dishes.count())  # DEBUG

#     data = list(dishes.values())
#     return JsonResponse({"cart_items": data})



# @login_required
# @csrf_exempt
# def place_order(req):
#     cart = req.session.get("cart", [])
#     print("GET_CART session cart:", cart)  # DEBUG
#     if not cart:
#         return JsonResponse({"error": "Cart is empty"}, status=400)

#     dishes = Menuu.objects.filter(DishId__in=cart)
#     print("GET_CART dishes count:", dishes.count())  # DEBUG
#     total = sum(int(d.Price) for d in dishes)

#     order_id = "ORD" + uuid.uuid4().hex[:8]
#     delivery_time = datetime.now() + timedelta(minutes=30)

#     order = Orderss.objects.create(
#         OrderId=order_id,
#         Userid=Userss.objects.get(Userid=req.user_payload["userid"]),
#         Items=list(dishes.values()),
#         TotalPrice=total,
#         ExpectedDelivery=delivery_time
#     )

#     req.session["cart"] = []   # clear cart

#     return JsonResponse({
#         "msg": "Order Placed Successfully",
#         "order_id": order.OrderId,
#         "total_price": total,
#         "expected_delivery": delivery_time.strftime("%I:%M %p"),
#     })


# Orders using DB instead of session

@login_required
@csrf_exempt
def add_to_cart(req, id):
    """
    Add a dish to the cart for the current JWT user.
    """
    try:
        dish_id = int(id)
    except ValueError:
        return JsonResponse({"error": "Invalid dish id"}, status=400)

    try:
        dish = Menuu.objects.get(DishId=dish_id)
    except Menuu.DoesNotExist:
        return JsonResponse({"error": "Dish not found"}, status=404)

    userid = req.user_payload.get("userid")
    try:
        user = Userss.objects.get(Userid=userid)
    except Userss.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    item, created = CartItem.objects.get_or_create(
        user=user,
        dish=dish,
        defaults={"quantity": 1},
    )
    if not created:
        item.quantity += 1
        item.save()

    return JsonResponse({"msg": "Item added to cart"})


@login_required
def get_cart(req):
    """
    Return all cart items for the current JWT user.
    """
    userid = req.user_payload.get("userid")
    try:
        user = Userss.objects.get(Userid=userid)
    except Userss.DoesNotExist:
        return JsonResponse({"cart_items": []})

    cart_items = CartItem.objects.filter(user=user).select_related("dish")

    data = []
    for ci in cart_items:
        d = ci.dish
        data.append({
            "DishId": d.DishId,
            "DishName": d.DishName,
            "Ingredients": d.Ingredients,
            "Category": d.Category,
            "Price": d.Price,
            "Image": d.Image,
            "quantity": ci.quantity,
        })

    return JsonResponse({"cart_items": data})


@login_required
@csrf_exempt
def place_order(req):
    """
    Create an order from the current user's cart items.
    """
    userid = req.user_payload.get("userid")
    try:
        user = Userss.objects.get(Userid=userid)
    except Userss.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    cart_items = CartItem.objects.filter(user=user).select_related("dish")

    if not cart_items.exists():
        return JsonResponse({"error": "Cart is empty"}, status=400)

    items_payload = []
    total = 0.0

    for ci in cart_items:
        d = ci.dish
        line_total = float(d.Price) * ci.quantity
        total += line_total
        items_payload.append({
            "DishId": d.DishId,
            "DishName": d.DishName,
            "Ingredients": d.Ingredients,
            "Category": d.Category,
            "Price": d.Price,
            "Image": d.Image,
            "quantity": ci.quantity,
            "line_total": line_total,
        })

    order_id = "ORD" + uuid.uuid4().hex[:8]
    delivery_time = datetime.now() + timedelta(minutes=30)

    order = Orderss.objects.create(
        OrderId=order_id,
        Userid=user,
        Items=items_payload,
        TotalPrice=total,
        ExpectedDelivery=delivery_time,
    )

    # clear the cart
    cart_items.delete()

    return JsonResponse({
        "msg": "Order Placed Successfully",
        "order_id": order.OrderId,
        "total_price": total,
        "expected_delivery": delivery_time.strftime("%I:%M %p"),
    })



def stripe_config(request):
    return JsonResponse({"publishableKey": settings.STRIPE_PUBLISHABLE_KEY})


@csrf_exempt
@login_required
@require_POST
def create_payment_intent(request):
    """
    POST JSON: { "order_id": "ORDxxxx" }
    Returns: { clientSecret, order_id, status, intent_id }
    """
    try:
        data = json.loads(request.body or "{}")
        order_id = data.get("order_id")
        if not order_id:
            return JsonResponse({"error": "order_id required"}, status=400)

        # fetch order
        try:
            order = Orderss.objects.get(OrderId=order_id)
        except Orderss.DoesNotExist:
            return JsonResponse({"error": "Order not found"}, status=404)

        # ensure order belongs to requesting user
        userid = request.user_payload.get("userid")
        if order.Userid.Userid != userid:
            return JsonResponse({"error": "Forbidden"}, status=403)

        amount_paise = int(round(float(order.TotalPrice) * 100))

        # If intent exists on order, retrieve it
        intent = None
        if getattr(order, "stripe_payment_intent_id", None):
            try:
                intent = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
            except Exception:
                intent = None

        # otherwise create one
        if not intent:
            intent = stripe.PaymentIntent.create(
                amount=amount_paise,
                currency="inr",
                automatic_payment_methods={"enabled": True},
                metadata={"order_id": str(order.OrderId)}
            )
            # save id for later reference
            order.stripe_payment_intent_id = intent.id
            order.save(update_fields=["stripe_payment_intent_id"])

        # Return client secret AND status + id so client can decide next action
        return JsonResponse({
            "clientSecret": intent.client_secret,
            "order_id": order.OrderId,
            "intent_id": intent.id,
            "status": intent.status
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
    if not endpoint_secret:
        # For safety: prefer CLI-provided secret in .env
        return HttpResponse("Webhook secret not configured", status=500)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle events we're interested in
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        order_id = intent.get("metadata", {}).get("order_id")
        if order_id:
            try:
                order = Orderss.objects.get(OrderId=order_id)
                order.paid = True
                order.Status = "Paid"
                order.save()
            except Orderss.DoesNotExist:
                pass

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        order_id = intent.get("metadata", {}).get("order_id")
        if order_id:
            try:
                order = Orderss.objects.get(OrderId=order_id)
                order.Status = "Payment Failed"
                order.save()
            except Orderss.DoesNotExist:
                pass

    # Acknowledge receipt
    return HttpResponse(status=200)




# @api_view(["POST"])
# @csrf_exempt
# def recommend_food(request):
#     if request.method != "POST":
#         return JsonResponse(
#             {"error": "Only POST method allowed"},
#             status=405
#         )

#     # ✅ Handle FORM DATA
#     mood = request.POST.get("mood")

#     if not mood:
#         return JsonResponse(
#             {"error": "Mood is required"},
#             status=400
#         )

#     # 🔥 Call AI service
#     ai_response = recommend_food_by_mood(mood)

#     return JsonResponse(
#         {
#             "mood": mood,
#             "recommendations": ai_response
#         },
#         safe=False
#     )


# @csrf_exempt
# def recommend_food(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "Only POST allowed"}, status=405)

#     mood = request.POST.get("mood")
#     if not mood:
#         return JsonResponse({"error": "Mood is required"}, status=400)

#     # 1️⃣ Get dish IDs from AI
#     dish_ids = recommend_food_by_mood(mood)

#     # 2️⃣ Fetch FULL menu items
#     dishes = Menuu.objects.filter(DishId__in=dish_ids)

#     # 3️⃣ Serialize (same shape as Menu.jsx expects)
#     data = []
#     for d in dishes:
#         data.append({
#             "DishId": d.DishId,
#             "DishName": d.DishName,
#             "Ingredients": d.Ingredients,
#             "Category": d.Category,
#             "Price": d.Price,
#             "Image": d.Image
#         })

#     return JsonResponse(
#         {
#             "mood": mood,
#             "items": data
#         }
#     )


# @csrf_exempt
# def recommend_food(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "POST only"}, status=405)

#     mood = request.POST.get("mood")
#     if not mood:
#         return JsonResponse({"error": "Mood required"}, status=400)

#     ai_results = recommend_food_by_mood(mood)

#     dish_ids = [x["DishId"] for x in ai_results]

#     dishes = Menuu.objects.filter(DishId__in=dish_ids)

#     # attach reason to each dish
#     response_data = []
#     for dish in dishes:
#         reason = next(
#             (x["reason"] for x in ai_results if x["DishId"] == dish.DishId),
#             ""
#         )
#         response_data.append({
#             "DishId": dish.DishId,
#             "DishName": dish.DishName,
#             "Ingredients": dish.Ingredients,
#             "Price": dish.Price,
#             "Image": dish.Image,
#             "reason": reason
#         })

#     return JsonResponse({
#         "mood": mood,
#         "items": response_data
#     })


# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services import recommend_food_by_mood
from rest_appp.models import Menuu

@csrf_exempt
def recommend_food(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    mood = request.POST.get("mood")
    if not mood:
        return JsonResponse({"error": "Mood required"}, status=400)

    ai_results = recommend_food_by_mood(mood)

    if not ai_results:
        return JsonResponse({"mood": mood, "items": []})

    dish_ids = [x["DishId"] for x in ai_results]

    dishes = Menuu.objects.filter(DishId__in=dish_ids)

    response_data = []
    for dish in dishes:
        reason = next(
            (x["reason"] for x in ai_results if x["DishId"] == dish.DishId),
            ""
        )
        response_data.append({
            "DishId": dish.DishId,
            "DishName": dish.DishName,
            "Price": dish.Price,
            "Image": dish.Image,
            "reason": reason
        })

    return JsonResponse({
        "mood": mood,
        "items": response_data
    })



def root_ok(request):
    return JsonResponse({"ok": True, "service": "rms"}, status=200)


