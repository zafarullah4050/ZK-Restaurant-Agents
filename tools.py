# tools.py
import json
from datetime import datetime

from order_state import order_state, reservation_state

# -------------------------------
# MENU TOOL
# -------------------------------
class MenuTool:
    name = "menu"
    description = "Show the restaurant menu."
    
    def func(self, query=""):
        try:
            with open("menu.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return "📋 Menu file not found. Please add menu.json in the project root."
        except Exception as e:
            return f"📋 Error reading menu: {e}"

        text = "📋 ZK Restaurant Menu\n\n"
        for cat, items in data.items():
            text += f"🍽 {cat}\n"
            for i in items:
                text += f"• {i.get('name')} — Rs {i.get('price')}\n"
            text += "\n"
        return text


# -------------------------------
# ORDER TOOL
# -------------------------------
class OrderTool:
    name = "order"
    description = "Place a new food order."

    def func(self, query, user):
        """
        Handles user order.
        Expected input: food item text.
        """
        item = (
            query.lower()
            .replace("order", "")
            .replace("confirm", "")
            .replace("please", "")
            .strip()
        )

        if not item:
            return "Kripya bataen ke aap kya order karna chahte hain."

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Save order into global state
        order_state[user] = {
            "item": item,
            "time": now,
            "status": "confirmed"
        }

        return f"🛒 Aapka order confirm ho gaya hai!\nItem: {item}\nTime: {now}\nShukriya ZK Restaurant choose karne ka! 🍽️"


# -------------------------------
# RESERVATION TOOL
# -------------------------------
class ReservationTool:
    name = "reserve"
    description = "Reserve a table."

    def func(self, query, user):
        details = query.strip() or "Table reservation"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        reservation_state[user] = {
            "details": details,
            "time": now,
            "status": "reserved"
        }

        return f"📅 Aapki table reserve ho gayi hai!\nDetails: {details}\nTime: {now} ✨"


# -------------------------------
# DELIVERY TOOL
# -------------------------------
class DeliveryTool:
    name = "delivery"
    description = "Check delivery availability."

    def func(self, location):
        location = (location or "").strip()
        areas = [
            "City Center", "Millat Road", "College Road", "Model Town",
            "Shahbaz Nagar", "Hospital Chowk", "Green Market Area"
        ]

        if not location:
            return "Please provide your delivery area (e.g. City Center)."
        if location in areas:
            return f"🚚 Delivery is available to {location}.\nDelivery Charges: Rs 70."
        else:
            return f"❌ Sorry, delivery is not available in {location}."


# -------------------------------
# UPSELL TOOL
# -------------------------------
class UpsellTool:
    name = "upsell"
    description = "Suggest an addon."

    def func(self, query=""):
        return "🔥 Recommendation: Add a chilled 1.5L drink to your order for just Rs 190!"


# -------------------------------
# COMPLAINT TOOL
# -------------------------------
class ComplaintTool:
    name = "complaint"
    description = "Register customer complaints."

    def func(self, query, user):
        text = query.strip() or "No details provided"
        return "🙏 Aapki complaint receive ho gayi hai. Humari team bohat jald aap se contact karegi."
