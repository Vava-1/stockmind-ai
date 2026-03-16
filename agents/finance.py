import logging

logger = logging.getLogger('StockMind-Finance')

class FinanceAgent:
    def __init__(self):
        self.agent_name = "Analyst"

    def calculate_margin(self, cost: float, price: float) -> float:
        """Calculates profit margin percentage."""
        if price <= 0: return 0.0
        return round(((price - cost) / price) * 100, 2)

    def analyze_profitability(self, inventory_data: list) -> dict:
        """Groups products by category to find the most profitable sectors."""
        categories = {}
        
        for item in inventory_data:
            cat = item.get('product_category', 'Unknown')
            cost = float(item.get('supplier_cost_usd', 0))
            price = float(item.get('retail_price_usd', 0))
            daily_sales = float(item.get('daily_sales_velocity', 0))
            
            if cat not in categories:
                categories[cat] = {
                    "item_count": 0,
                    "total_daily_revenue": 0.0,
                    "margins": []
                }
                
            categories[cat]["item_count"] += 1
            categories[cat]["total_daily_revenue"] += (price * daily_sales)
            categories[cat]["margins"].append(self.calculate_margin(cost, price))
            
        # Clean up the averages
        for cat in categories:
            margins = categories[cat]["margins"]
            categories[cat]["avg_margin_percent"] = round(sum(margins) / len(margins), 2) if margins else 0
            categories[cat]["total_daily_revenue"] = round(categories[cat]["total_daily_revenue"], 2)
            del categories[cat]["margins"] # Remove raw list to keep JSON clean
            
        return categories

# Global instance
finance_agent = FinanceAgent()
