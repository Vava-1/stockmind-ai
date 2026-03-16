import logging
from datetime import datetime

logger = logging.getLogger('StockMind-Negotiator')

class NegotiatorAgent:
    def __init__(self):
        self.agent_name = "Advisor"

    def calc_reorder_point(self, daily_sales: float, lead_time: int) -> int:
        """Calculates when to trigger an order (includes 1.5x safety stock)."""
        return round(daily_sales * lead_time * 1.5)

    def calculate_reorder_qty(self, current_stock: int, daily_sales: float, lead_time: int) -> int:
        """Calculates exactly how many units to buy."""
        reorder_point = self.calc_reorder_point(daily_sales, lead_time)
        # We want to buy enough to cover the reorder point + 14 days of future sales
        target_stock = (reorder_point * 2) + (daily_sales * 14)
        qty_to_buy = max(0, int(target_stock - current_stock))
        return qty_to_buy

    def draft_purchase_order(self, product_id: str, qty: int, supplier_name: str, cost: float) -> str:
        """Autonomously drafts a professional email to the supplier."""
        total_cost = qty * cost
        
        po_text = f"""
        Subject: Purchase Order Request - {product_id} (GIVA TECH LTD)
        
        To the Sales Team at {supplier_name},
        
        Please consider this an official Purchase Order from GIVA TECH LTD. 
        We would like to request a restock of the following item:
        
        Product ID: {product_id}
        Requested Quantity: {qty} Units
        Agreed Unit Cost: ${cost:.2f}
        Total Estimated PO Value: ${total_cost:,.2f}
        
        Please confirm receipt of this order and provide an estimated shipping date.
        
        Thank you,
        StockMind AI (Autonomous Procurement System)
        On behalf of GIVA TECH LTD
        """
        return po_text.strip()

# Global instance
negotiator_agent = NegotiatorAgent()
