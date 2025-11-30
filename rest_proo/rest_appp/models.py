from django.db import models

class Menuu(models.Model):
    DishId=models.IntegerField(primary_key=True)
    DishName=models.CharField(max_length=50)
    Ingredients=models.TextField()
    Category=models.CharField(max_length=20)
    Price=models.FloatField()
    Image=models.URLField()

class Userss(models.Model):
    Userid=models.IntegerField(primary_key=True)
    Username=models.CharField(max_length=50)
    Email=models.EmailField(max_length=50,null=False,unique=True)
    Password=models.CharField(max_length=225,null=False)
    Role=models.CharField(max_length=20, default='User')


class Orderss(models.Model):
    OrderId = models.CharField(max_length=20, primary_key=True)
    Userid = models.ForeignKey(Userss, on_delete=models.CASCADE)
    Items = models.JSONField()    # list of ordered items like [{'DishId': 'D01', 'Qty': 2, 'Price': 200}]
    TotalPrice = models.IntegerField()
    Status = models.CharField(max_length=20, default="Confirmed")
    OrderedTime = models.DateTimeField(auto_now_add=True)
    ExpectedDelivery = models.DateTimeField()

# NEW
class CartItem(models.Model):
    user = models.ForeignKey(Userss, on_delete=models.CASCADE)
    dish = models.ForeignKey(Menuu, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)