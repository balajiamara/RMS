# from openai import OpenAI
# from django.conf import settings
# from rest_appp.models import Menuu   # change app name if needed

# client = OpenAI(api_key=settings.OPENAI_API_KEY)


# def recommend_food_by_mood(mood):
#     # 1️⃣ Get menu items that match the mood
#     items = Menuu.objects.filter(mood_tags__contains=[mood])

#     if not items.exists():
#         return []

#     # 2️⃣ Prepare menu for AI
#     menu_data = []
#     for item in items:
#         menu_data.append({
#             "DishId": item.DishId,
#             "DishName": item.DishName,
#             "Category": item.Category,
#             "food_tags": item.food_tags,
#             "Price": item.Price
#         })

#     # 3️⃣ AI prompt
#     prompt = f"""
# You are an AI food recommendation assistant.

# RULES:
# - Recommend ONLY from the menu list below
# - Do NOT invent items
# - Suggest maximum 3 dishes
# - Give short reasons

# User mood: {mood}

# Menu:
# {menu_data}
# """

#     # 4️⃣ Call OpenAI
#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {"role": "user", "content": prompt}
#         ]
#     )

#     # 5️⃣ Return AI response text
#     return response.choices[0].message.content



# from openai import OpenAI
# from django.conf import settings
# from rest_appp.models import Menuu
# import json

# client = OpenAI(api_key=settings.OPENAI_API_KEY)


# def recommend_food_by_mood(mood):
#     # 1️⃣ Get menu items that match the mood
#     items = Menuu.objects.filter(mood_tags__contains=[mood])

#     if not items.exists():
#         return []

#     # 2️⃣ Prepare minimal menu data for AI
#     menu_data = []
#     for item in items:
#         menu_data.append({
#             "DishId": item.DishId,
#             "DishName": item.DishName,
#             "food_tags": item.food_tags,
#             "Category": item.Category
#         })

#     # 3️⃣ AI prompt (STRICT JSON OUTPUT)
#     prompt = f"""
# You are an AI food recommendation assistant.

# RULES:
# - Choose ONLY from the menu list below
# - Do NOT invent items
# - Return ONLY valid JSON
# - Select maximum 3 dishes

# User mood: {mood}

# Menu:
# {menu_data}

# Return format:
# {{
#   "recommended_dish_ids": [1, 2, 3]
# }}
# """

#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[{"role": "user", "content": prompt}]
#     )

#     # 4️⃣ Parse AI response safely
#     ai_text = response.choices[0].message.content

#     try:
#         ai_json = json.loads(ai_text)
#         return ai_json.get("recommended_dish_ids", [])
#     except Exception:
#         return []



from openai import OpenAI
from django.conf import settings
from rest_appp.models import Menuu
import json

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def recommend_food_by_mood(mood):
    items = Menuu.objects.filter(mood_tags__contains=[mood])

    if not items.exists():
        return []

    menu_data = []
    for item in items:
        menu_data.append({
            "DishId": item.DishId,
            "DishName": item.DishName,
            "food_tags": item.food_tags,
            "Category": item.Category
        })

    prompt = f"""
You are a food recommendation assistant.

Return ONLY valid JSON.
Pick maximum 3 dishes.

Format:
[
  {{ "DishId": number, "reason": string }}
]

User mood: {mood}

Menu:
{menu_data}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return []
