"""
Amazon CSV order importer for reconciliation.
This reads Amazon order reports that you download manually.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)


class AmazonCSVImporter:
    """Import Amazon orders from CSV reports."""

    def __init__(self):
        """Initialize the CSV importer."""
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.data_dir.mkdir(exist_ok=True)

    def import_orders_csv(self, csv_path: Optional[str] = None) -> List[Dict]:
        """
        Import Amazon orders from CSV file.

        Args:
            csv_path: Path to CSV file (optional, defaults to data/amazon_orders.csv)

        Returns:
            List of order dictionaries
        """
        if not csv_path:
            csv_path = self.data_dir / 'amazon_orders.csv'

        if not Path(csv_path).exists():
            logger.error(f"CSV file not found: {csv_path}")
            return []

        orders = []

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Parse Amazon CSV format
                    # Common columns: Order Date, Order ID, Title, Category, Total, Payment Method

                    order_date = self._parse_date(row.get('Order Date', ''))
                    if not order_date:
                        continue

                    # Extract amount
                    total_str = row.get('Item Total', row.get('Total', '0'))
                    total = self._parse_amount(total_str)

                    order = {
                        'order_id': row.get('Order ID', f"CSV-{datetime.now().timestamp()}"),
                        'date': order_date,
                        'total': total,
                        'subtotal': total * 0.92,  # Estimate subtotal
                        'tax': total * 0.08,  # Estimate tax
                        'items': [{
                            'name': row.get('Title', 'Amazon Purchase'),
                            'category': row.get('Category', 'Shopping'),
                            'asin': self._extract_asin(row.get('ASIN/ISBN', '')),
                            'price': total,
                            'quantity': int(row.get('Quantity', 1)),
                            'link': row.get('Product Link', '')
                        }],
                        'status': row.get('Order Status', 'Delivered'),
                        'payment_method': self._map_payment_method(row.get('Payment Instrument Type', ''))
                    }

                    orders.append(order)

            logger.info(f"Imported {len(orders)} orders from CSV")
            return orders

        except Exception as e:
            logger.error(f"Failed to import CSV: {str(e)}")
            return []

    def import_orders_json(self, json_path: Optional[str] = None) -> List[Dict]:
        """
        Import Amazon orders from JSON file (alternative format).

        Args:
            json_path: Path to JSON file

        Returns:
            List of order dictionaries
        """
        if not json_path:
            json_path = self.data_dir / 'amazon_orders.json'

        if not Path(json_path).exists():
            logger.error(f"JSON file not found: {json_path}")
            return []

        try:
            with open(json_path, 'r') as f:
                orders = json.load(f)

            # Convert dates from strings
            for order in orders:
                if isinstance(order.get('date'), str):
                    order['date'] = self._parse_date(order['date']) or datetime.fromisoformat(order['date'])

            logger.info(f"Imported {len(orders)} orders from JSON")
            return orders

        except Exception as e:
            logger.error(f"Failed to import JSON: {str(e)}")
            return []

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from various formats."""
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m/%d/%y',
            '%B %d, %Y',
            '%b %d, %Y'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue

        return None

    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount from string."""
        # Remove currency symbols and commas
        amount_str = re.sub(r'[^0-9.]', '', amount_str)
        try:
            return float(amount_str)
        except:
            return 0.0

    def _extract_asin(self, asin_str: str) -> str:
        """Extract ASIN from string."""
        # ASIN is typically 10 alphanumeric characters
        match = re.search(r'[A-Z0-9]{10}', asin_str)
        return match.group(0) if match else asin_str

    def _map_payment_method(self, payment_str: str) -> str:
        """Map payment method to YNAB account name."""
        payment_lower = payment_str.lower()

        mappings = {
            'amazon': 'Amazon Business Prime Card',
            'chase': 'Chase Reserve CC',
            'apple': 'Apple Card',
            'amex': 'SimplyCash® Plus Card',
            'american express': 'SimplyCash® Plus Card'
        }

        for key, value in mappings.items():
            if key in payment_lower:
                return value

        return payment_str


def download_instructions():
    """Print instructions for downloading Amazon orders."""
    print("\n" + "="*60)
    print("HOW TO DOWNLOAD AMAZON ORDER REPORTS")
    print("="*60)
    print("\n1. Go to: https://www.amazon.com/gp/b2b/reports")
    print("   OR")
    print("   Go to: Your Account → Download order reports")
    print("\n2. Select:")
    print("   - Report Type: 'Items'")
    print("   - Start Date: (30 days ago)")
    print("   - End Date: Today")
    print("\n3. Click 'Request Report'")
    print("\n4. Once ready, download the CSV")
    print("\n5. Save to:")
    print(f"   {Path(__file__).parent.parent / 'data' / 'amazon_orders.csv'}")
    print("\n6. Run reconciliation:")
    print("   python3 src/reconciler_main.py --use-csv --days 30")
    print("="*60)


if __name__ == "__main__":
    # Test the importer
    importer = AmazonCSVImporter()

    # Show download instructions
    download_instructions()

    # Check if CSV exists
    csv_path = importer.data_dir / 'amazon_orders.csv'
    if csv_path.exists():
        print(f"\n✓ Found CSV at: {csv_path}")
        orders = importer.import_orders_csv()
        print(f"✓ Imported {len(orders)} orders")

        if orders:
            print("\nSample orders:")
            for order in orders[:3]:
                print(f"  - {order['date'].strftime('%Y-%m-%d')}: ${order['total']:.2f} - {order['items'][0]['name'][:50]}")
    else:
        print(f"\n✗ No CSV found at: {csv_path}")
        print("  Please download your Amazon order report first.")