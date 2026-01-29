from django.urls import path
from . import views 

urlpatterns=[
    path('add_item/',view=views.add_dish, name='add_item'),
    path('show_item/',view=views.get_dish),
    path('modify_item/<str:id>/',view=views.update_dish),
    path('remove_item/<str:id>/',view=views.del_dish),

    
    path('show_users/',view=views.get_users),
    path('get_user/<str:id>/', views.get_user),
    path('auth/register/',view=views.reg_user),
    path('modify_user/<str:id>/',view=views.update_user),
    path('remove_user/<str:id>/',view=views.del_user),
    path('auth/login/', view=views.login),
    path('promote_user/<str:id>/', views.promote_user, name='promote_user'),
    path("modify_my_details/", views.modify_my_details, name="modify_my_details"),
    path('whoami/', views.whoami),

    
    # 🚀 CART + ORDER (Required for Orders page)
    path('add_to_cart/<str:id>/', views.add_to_cart, name='add_to_cart'),
    path('get_cart/', views.get_cart, name='get_cart'),
    path('place_order/', views.place_order, name='place_order'),
    # path('orders/', views.orders_page, name='orders_page')


    path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    path("config/stripe-publishable-key/", views.stripe_config, name="stripe-config"),

    path("recommend/", views.recommend_food, name="ai-recommend-food"),

    # Order History
    path('my_orders/', views.get_user_orders, name='my_orders'),
]



    # path('send_attachment_mail/', view=views.send_attachment_mail)