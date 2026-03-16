import logging
from core.database import execute_query

logger = logging.getLogger('StockMind-Monitor')

class MonitorAgent:
    def __init__(self):
        self.agent_name = "Monitor"

    def days_left(self, stock: int, daily_sales: float) -> float:
        """Calculates how many days of stock remain."""
        if daily_sales <= 0: return 999.0
        return round(stock / daily_sales, 1)

    def stock_status(self, stock: int, daily_sales: float, lead_time: int) -> str:
        """Classifies the severity of the stock level."""
        if stock <= 0: return 'OUT_OF_STOCK'
        
        d_left = self.days_left(stock, daily_sales)
        
        # If days left is less than the time it takes to get new stock, it's critical
        if d_left <= lead_time: return 'CRITICAL'
        # If we only have a 3-day buffer above lead time, it's a warning
        if d_left <= (lead_time + 3): return 'WARNING'
        
        return 'SAFE'

    def analyze_inventory_health(self, inventory_data: list) -> dict:
        """Scans the entire database and groups items by urgency."""
        report = {
            "OUT_OF_STOCK": [],
            "CRITICAL": [],
            "WARNING": [],
            "SAFE_COUNT": 0
        }
        
        for item in inventory_data:
            stock = item.get('current_stock', 0)
            daily_sales = item.get('daily_sales_velocity', 0)
            lead_time = item.get('lead_time_days', 7)
            
            status = self.stock_status(stock, daily_sales, lead_time)
            
            if status == 'SAFE':
                report["SAFE_COUNT"] += 1
            else:
                report[status].append({
                    "product_id": item.get('product_id'),
                    "category": item.get('product_category'),
                    "stock": stock,
                    "days_left": self.days_left(stock, daily_sales),
                    "supplier": item.get('supplier_name')
                })
                
        return report

# Global instance
monitor_agent = MonitorAgent()
