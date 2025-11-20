from rest_framework import serializers
from .models import Menuu, Userss

# Validation Logic for Image
def validate_img(image):
    max_size = 3*1024*1024      #3MB
    allowed_types=['image/jpeg', 'image/png']

    if image.size > max_size:
        raise serializers.ValidationError('Image is too large. Please upload a Image less than 3MB')
    
    if image.content_type  not in allowed_types:
        raise serializers.ValidationError('Only JPEG or PNG formats are allowed')
    
    return image




class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model=Menuu              #we can assign in 2 ways
        fields='__all__'        #1st way

    
    def validate_Image(self, value):            # <-- Must match your model field name!
        if isinstance(value,str):               #  If value is a URL string (not a file), no size/type checks needed
            return value
        
        return validate_img(value)
        


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=Userss
        fields=['Userid', 'Username', 'Email', 'Password']      #2nd way

