from decimal import Decimal

from django.test import TestCase

from .models import Item
from .tools import add_item, calculate_cost, check_stock, list_items, remove_stock


class InventoryTests(TestCase):
    def setUp(self):
        self.item = Item.objects.create(
            name="chocolate bar", quantity=10, price=Decimal("2.00")
        )

    def test_cost_with_vat(self):
        result = calculate_cost("Chocolate Bar", 3, 10)
        self.assertEqual(result["unit_price"], "2.00")
        self.assertEqual(result["subtotal"], "6.00")
        self.assertEqual(result["vat_amount"], "0.60")
        self.assertEqual(result["total"], "6.60")
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 10)

    def test_cost_without_vat(self):
        result = calculate_cost("chocolate bar", 3)
        self.assertEqual(result["vat_amount"], "0.00")
        self.assertEqual(result["total"], "6.00")

    def test_vat_rounding(self):
        self.item.price = Decimal("0.05")
        self.item.save()
        result = calculate_cost("chocolate bar", 1, 10)
        self.assertEqual(result["vat_amount"], "0.01")
        self.assertEqual(result["total"], "0.06")

    def test_invalid_cost_requests(self):
        self.assertIn("error", calculate_cost("missing item", 3, 10))
        self.assertIn("error", calculate_cost("chocolate bar", 0, 10))
        self.assertIn("error", calculate_cost("chocolate bar", 1.5, 10))
        self.assertIn("error", calculate_cost("chocolate bar", 3, -10))

    def test_add_item_and_keep_price_when_restocking(self):
        add_item("biscuit", 4, 1.50)
        add_item("biscuit", 2)
        item = Item.objects.get(name="biscuit")
        self.assertEqual(item.quantity, 6)
        self.assertEqual(item.price, Decimal("1.50"))
        add_item("biscuit", 1, 1.75)
        item.refresh_from_db()
        self.assertEqual(item.price, Decimal("1.75"))

    def test_invalid_stock_changes(self):
        self.assertIn("error", add_item("biscuit", 2, -1))
        self.assertIn("error", add_item("biscuit", 2))
        self.assertIn("error", remove_stock("chocolate bar", -1))
        self.assertIn("error", remove_stock("chocolate bar", 11))
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 10)

    def test_stock_tools_include_price(self):
        self.assertEqual(check_stock("chocolate bar")["price"], "2.00")
        self.assertEqual(list_items()["items"][0]["price"], "2.00")

    def test_chat_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "10% VAT")
