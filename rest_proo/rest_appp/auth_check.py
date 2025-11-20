# rest_app/auth_check.py
import jwt
from functools import wraps
from django.http import JsonResponse
from datetime import datetime
from django.conf import settings

SECRETKEY = settings.SECRET_KEY

def _get_token_from_request(req):
    # 1) Try cookie first (your login sets my_cookie)
    token = req.COOKIES.get('my_cookie')
    if token:
        return token

    # 2) Fallback to Authorization header: "Bearer <token>"
    auth = req.META.get('HTTP_AUTHORIZATION', '')
    if auth.startswith('Bearer '):
        return auth.split(' ', 1)[1].strip()

    return None

def _decode_token(token):
    # raise jwt exceptions as-is to caller (we catch them in decorators)
    payload = jwt.decode(token, SECRETKEY, algorithms=['HS256'])
    return payload

def login_required(view_func):
    @wraps(view_func)
    def wrapper(req, *args, **kwargs):
        try:
            token = _get_token_from_request(req)
            if not token:
                # Not logged in
                return JsonResponse({'error': 'Authentication required'}, status=401)

            payload = _decode_token(token)

            # Attach payload to request for downstream views
            req.user_payload = payload

            # (optional) debug print
            print("login_required: decoded payload:", payload)

            return view_func(req, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            print("login_required: token expired")
            return JsonResponse({'error': 'Token expired'}, status=401)
        except jwt.InvalidTokenError as e:
            print("login_required: invalid token:", repr(e))
            return JsonResponse({'error': 'Invalid token'}, status=401)
        except Exception as e:
            print("login_required: unexpected error:", repr(e))
            return JsonResponse({'error': 'Authentication error', 'details': str(e)}, status=500)

    return wrapper

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(req, *args, **kwargs):
        try:
            token = _get_token_from_request(req)
            if not token:
                return JsonResponse({'error': 'Authentication required'}, status=401)

            payload = _decode_token(token)
            req.user_payload = payload

            # Debug print
            print("admin_required: decoded payload:", payload)

            role = payload.get('role') or payload.get('Role') or ''
            role_norm = str(role).strip().lower()

            if role_norm != 'admin':
                # Not an admin
                return JsonResponse({'error': 'Admin only access'}, status=403)

            return view_func(req, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            print("admin_required: token expired")
            return JsonResponse({'error': 'Token expired'}, status=401)
        except jwt.InvalidTokenError as e:
            print("admin_required: invalid token:", repr(e))
            return JsonResponse({'error': 'Invalid token'}, status=401)
        except Exception as e:
            print("admin_required: unexpected error:", repr(e))
            return JsonResponse({'error': 'Authorization error', 'details': str(e)}, status=500)

    return wrapper
