# agent_tools.py

"""
Wrap the tool classes defined in tools.py into a simple structure the app expects.
"""

from tools import MenuTool, OrderTool, ReservationTool, DeliveryTool, UpsellTool, ComplaintTool

class ToolWrapper:
    def __init__(self, name, func, description: str = ""):
        self.name = name
        self.func = func
        self.description = description

# All tools must be correctly passed with their .func reference
tools = [
    ToolWrapper("menu", MenuTool().func, "Show the restaurant menu"),
    ToolWrapper("order", OrderTool().func, "Place an order"),  # CORRECT
    ToolWrapper("reserve", ReservationTool().func, "Book a table"),
    ToolWrapper("delivery", DeliveryTool().func, "Delivery check"),
    ToolWrapper("upsell", UpsellTool().func, "Suggest add-ons"),
    ToolWrapper("complaint", ComplaintTool().func, "Log a complaint"),
]
