from django.urls import path
from . import views 

urlpatterns=[
    path('add_item/',view=views.add_dish, name='add_item'),
    path('show_item/',view=views.get_dish),
    path('modify_item/<str:id>/',view=views.update_dish),
    path('remove_item/<str:id>/',view=views.del_dish),

    
    path('show_users/',view=views.get_users),
    path('add_user/',view=views.reg_user),
    path('modify_user/<str:id>/',view=views.update_user),
    path('remove_user/<str:id>/',view=views.del_user),
    path('login_user/', view=views.login),
    path('promote_user/<str:id>/', views.promote_user, name='promote_user'),
    path("modify_my_details/", views.modify_my_details, name="modify_my_details")

]



    # path('send_attachment_mail/', view=views.send_attachment_mail)