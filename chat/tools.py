from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .models import Item


def check_stock(name):
    """Look up how many of an item we have."""
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    return {"name": item.name, "quantity": item.quantity, "price": str(item.price)}


def list_items():
    """Return every item in the inventory."""
    items = Item.objects.all()
    return {"items": [
        {"name": i.name, "quantity": i.quantity, "price": str(i.price)}
        for i in items
    ]}


def add_item(name, quantity, price=None):
    """Create a new item, or add to an existing one's stock."""
    if type(quantity) is not int or quantity <= 0:
        return {"error": "Quantity must be a positive whole number."}

    if price is not None:
        try:
            price = Decimal(str(price))
        except InvalidOperation:
            return {"error": "Price must be a number."}
        if not price.is_finite() or price < 0 or price > Decimal("99999999.99"):
            return {"error": "Price must be between 0 and 99999999.99."}
        price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    item = Item.objects.filter(name__iexact=name).first()
    if item is not None:
        item.quantity += quantity
        if price is not None:
            item.price = price
        item.save()
        return {"name": item.name, "quantity": item.quantity,
                "price": str(item.price), "created": False}

    if price is None:
        return {"error": "Please provide the unit price for the new item."}
    item = Item.objects.create(name=name, quantity=quantity, price=price)
    return {"name": item.name, "quantity": item.quantity,
            "price": str(item.price), "created": True}


def calculate_cost(name, quantity, vat_percent=0):
    """Calculate the cost of several units, including VAT."""
    if type(quantity) is not int or quantity <= 0:
        return {"error": "Quantity must be a positive whole number."}

    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}

    try:
        vat_percent = Decimal(str(vat_percent))
    except InvalidOperation:
        return {"error": "VAT must be a number."}
    if not vat_percent.is_finite() or not 0 <= vat_percent <= 100:
        return {"error": "VAT must be between 0 and 100 percent."}

    subtotal = item.price * quantity
    vat_amount = (subtotal * vat_percent / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total = subtotal + vat_amount

    return {
        "name": item.name,
        "quantity": quantity,
        "unit_price": str(item.price),
        "subtotal": str(subtotal),
        "vat_percent": str(vat_percent),
        "vat_amount": str(vat_amount),
        "total": str(total),
    }


def remove_stock(name, quantity):
    """Take a quantity out of stock."""
    if type(quantity) is not int or quantity <= 0:
        return {"error": "Quantity must be a positive whole number."}
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    if quantity > item.quantity:
        return {
            "error": f"Cannot remove {quantity}. Only {item.quantity} in stock.",
            "name": item.name,
            "quantity": item.quantity,
        }
    item.quantity -= quantity
    item.save()
    return {"name": item.name, "quantity": item.quantity}


def delete_item(name):
    """Remove an item from the inventory entirely."""
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    item.delete()
    return {"deleted": name}


TOOL_DECLARATIONS = [
    {
        "type": "function",
        "name": "check_stock",
        "description": "Look up the quantity and unit price of an item. Use this for stock or single-item price questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the item, e.g. 'Hammer'.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "type": "function",
        "name": "list_items",
        "description": "Return every item with its quantity and unit price. Use this when the user asks for a list of the inventory.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "add_item",
        "description": "Add stock or create an item. A unit price is needed for a new item. For an existing item, keep its price unless the user explicitly supplies a new price.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the item, e.g. 'Hammer'.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "How many units to add. Must be positive.",
                },
                "price": {
                    "type": "number",
                    "description": "Price of one unit before VAT. Must be non-negative.",
                },
            },
            "required": ["name", "quantity"],
        },
    },
    {
        "type": "function",
        "name": "remove_stock",
        "description": "Reduce the quantity of an existing item. Use this when items are sold, shipped or used. This does NOT delete the item; it only lowers the number.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the item, e.g. 'Hammer'.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "How many units to remove. Must be positive.",
                },
            },
            "required": ["name", "quantity"],
        },
    },
    {
        "type": "function",
        "name": "delete_item",
        "description": "Permanently remove an item and its record from the inventory entirely. This is destructive. Only use it when the user clearly wants the item gone, not when they want to reduce its quantity.",
        "parameters": {
            "type": "object",
            "properties": {

                "name": {
                    "type": "string",
                    "description": "The name of the item to delete.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "type": "function",
        "name": "calculate_cost",
        "description": "Calculate the total cost of a quantity using its stored unit price, including VAT. This is a price quotation and does not change stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The item name as stored in the inventory.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "The number of units to price. Must be positive.",
                },
                "vat_percent": {
                    "type": "number",
                    "description": "VAT as a percentage, e.g. 10 for 10%. Use 0 if none is requested.",
                },
            },
            "required": ["name", "quantity"],
        },
    },
]

TOOL_FUNCTIONS = {
    "check_stock": check_stock,
    "list_items": list_items,
    "add_item": add_item,
    "remove_stock": remove_stock,
    "delete_item": delete_item,
    "calculate_cost": calculate_cost,
}
