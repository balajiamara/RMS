from openai import OpenAI
from django.conf import settings
from rest_appp.models import Menuu   # change app name if needed

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def recommend_food_by_mood(mood):
    # 1️⃣ Get menu items that match the mood
    items = Menuu.objects.filter(mood_tags__contains=[mood])

    if not items.exists():
        return []

    # 2️⃣ Prepare menu for AI
    menu_data = []
    for item in items:
        menu_data.append({
            "DishId": item.DishId,
            "DishName": item.DishName,
            "Category": item.Category,
            "food_tags": item.food_tags,
            "Price": item.Price
        })

    # 3️⃣ AI prompt
    prompt = f"""
You are an AI food recommendation assistant.

RULES:
- Recommend ONLY from the menu list below
- Do NOT invent items
- Suggest maximum 3 dishes
- Give short reasons

User mood: {mood}

Menu:
{menu_data}
"""

    # 4️⃣ Call OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # 5️⃣ Return AI response text
    return response.choices[0].message.content
