"""
Amazon CSV order importer for reconciliation.
This reads Amazon order reports that you download manually or from the Downloads folder.
"""

import csv
import json
import logging
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re

logger = logging.getLogger(__name__)


class AmazonCSVImporter:
    """Import Amazon orders from CSV reports."""

    def __init__(self, downloads_dir: str = None):
        """
        Initialize the CSV importer.

        Args:
            downloads_dir: Path to downloads directory to check for CSV files
        """
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.data_dir.mkdir(exist_ok=True)
        self.downloads_dir = Path(downloads_dir or os.path.expanduser("~/Downloads"))

        # State file for tracking processed downloads
        self.state_file = self.data_dir / 'csv_import_state.json'
        self.state = self._load_state()

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
            # Handle BOM in CSV files
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Parse Amazon CSV format - handle both standard and Business formats
                    # Business format: Order Date, Order ID, Title, Order Net Total, Item Net Total
                    # Standard format: Order Date, Order ID, Title, Item Total, Total

                    order_date = self._parse_date(row.get('Order Date', ''))
                    if not order_date:
                        continue

                    # Extract amount - try multiple column names
                    total_str = (row.get('Item Net Total') or
                                row.get('Order Net Total') or
                                row.get('Item Total') or
                                row.get('Total') or '0')
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
        """Parse date from various formats with intelligent year validation.

        Validates that dates are within reasonable bounds:
        - Not more than 1 year in the future (likely data error)
        - Not more than 3 years in the past (outside typical lookback)
        """
        formats = [
            '%m/%d/%Y',  # MM/DD/YYYY format (most common for Amazon)
            '%Y-%m-%d',
            '%m/%d/%y',
            '%B %d, %Y',
            '%b %d, %Y'
        ]

        current_date = datetime.now()
        max_future_date = current_date + timedelta(days=365)
        min_past_date = current_date - timedelta(days=365 * 3)

        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)

                # Validate date is within reasonable bounds
                if parsed_date > max_future_date:
                    # Date is too far in future - likely a data error
                    # Try adjusting to current year first
                    adjusted = parsed_date.replace(year=current_date.year)
                    if adjusted > max_future_date:
                        # Still in future, try previous year
                        adjusted = parsed_date.replace(year=current_date.year - 1)
                    logger.debug(f"Adjusted future date: {date_str} -> {adjusted.date()}")
                    return adjusted
                elif parsed_date < min_past_date:
                    # Date is very old - log warning but still use it
                    logger.warning(f"Date {date_str} is more than 3 years in the past")

                return parsed_date
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
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

        # Check for card numbers in the string
        if '3008' in payment_str:
            return 'Amazon Business Prime Card – 3008'
        elif '1010' in payment_str:
            return 'Amazon Business Prime Card – 1010'
        elif '1516' in payment_str:
            return 'Chase Reserve CC – 1516'
        elif '4008' in payment_str:
            return 'SimplyCash® Plus Card – 4008'
        elif '5634' in payment_str:
            # This appears to be a Visa card
            return 'Chase Reserve CC – 1516'  # Assuming this is the Chase card

        # Fallback to general mappings
        mappings = {
            'rewards account': 'Amazon Business Prime Card – 3008',  # Amazon rewards
            'amazon': 'Amazon Business Prime Card – 3008',
            'chase': 'Chase Reserve CC – 1516',
            'apple': 'Apple Card',
            'amex ending in 3008': 'Amazon Business Prime Card – 3008',
            'american express ending in 3008': 'Amazon Business Prime Card – 3008',
            'amex': 'SimplyCash® Plus Card – 4008',
            'american express': 'SimplyCash® Plus Card – 4008'
        }

        for key, value in mappings.items():
            if key in payment_lower:
                return value

        # If no mapping found, return original
        return payment_str

    def _load_state(self) -> Dict:
        """Load processing state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading state file: {e}")
        return {'processed_files': {}}

    def _save_state(self):
        """Save processing state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving state file: {e}")

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def find_latest_amazon_csv(self, since: datetime = None) -> Optional[Path]:
        """
        Find the latest Amazon CSV file in downloads folder.

        Args:
            since: Only find files modified after this datetime

        Returns:
            Path to latest Amazon CSV file or None if not found
        """
        if not self.downloads_dir.exists():
            logger.warning(f"Downloads directory does not exist: {self.downloads_dir}")
            return None

        # Set default 'since' to 7 days ago if not provided
        if since is None:
            since = datetime.now() - timedelta(days=7)

        # Patterns to match Amazon CSV files
        patterns = [
            '*amazon*.csv', '*Amazon*.csv',
            '*order*.csv', '*Order*.csv',
            '*purchase*.csv', '*Purchase*.csv',
            '*transaction*.csv', '*Transaction*.csv'
        ]

        matching_files = []
        for pattern in patterns:
            for file_path in self.downloads_dir.glob(pattern):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime >= since and file_path.stat().st_size > 100:
                        # Verify it's an Amazon CSV by checking headers
                        if self._is_amazon_csv(file_path):
                            matching_files.append(file_path)

        if not matching_files:
            logger.info("No Amazon CSV files found in downloads folder")
            return None

        # Sort by modification time (newest first) and return latest
        matching_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        latest = matching_files[0]

        # Check if already processed
        file_hash = self._get_file_hash(latest)
        if file_hash in self.state.get('processed_files', {}):
            logger.info(f"Latest CSV already processed: {latest.name}")
            # Look for next unprocessed file
            for csv_file in matching_files[1:]:
                file_hash = self._get_file_hash(csv_file)
                if file_hash not in self.state.get('processed_files', {}):
                    logger.info(f"Found unprocessed CSV: {csv_file.name}")
                    return csv_file
            return None

        logger.info(f"Found latest Amazon CSV: {latest.name}")
        return latest

    def _is_amazon_csv(self, file_path: Path) -> bool:
        """
        Verify if a CSV file is an Amazon order report by checking headers.

        Args:
            file_path: Path to CSV file

        Returns:
            True if file appears to be Amazon order report
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read first line (headers)
                first_line = f.readline().lower()

                # Check for Amazon-specific headers
                amazon_indicators = [
                    'order', 'amazon', 'asin', 'item', 'purchase',
                    'product', 'title', 'category', 'shipment'
                ]

                matches = sum(1 for indicator in amazon_indicators
                            if indicator in first_line)

                return matches >= 2  # At least 2 indicators present

        except Exception as e:
            logger.debug(f"Could not verify CSV file {file_path}: {e}")
            return False

    def import_from_downloads(self, since: datetime = None) -> Tuple[List[Dict], Optional[Path]]:
        """
        Import Amazon orders from the latest CSV in downloads folder.

        Args:
            since: Only check files modified after this datetime

        Returns:
            Tuple of (orders list, path to CSV file processed)
        """
        csv_path = self.find_latest_amazon_csv(since)

        if not csv_path:
            logger.info("No unprocessed Amazon CSV files found in downloads")
            return [], None

        logger.info(f"Importing from downloads: {csv_path.name}")
        orders = self.import_orders_csv(str(csv_path))

        if orders:
            # Mark as processed
            file_hash = self._get_file_hash(csv_path)
            self.state['processed_files'][file_hash] = {
                'file_name': csv_path.name,
                'processed_at': datetime.now().isoformat(),
                'order_count': len(orders),
                'file_size': csv_path.stat().st_size
            }
            self._save_state()

            logger.info(f"Successfully imported {len(orders)} orders from {csv_path.name}")

        return orders, csv_path

    def archive_csv(self, csv_path: Path, archive_dir: Path = None) -> Path:
        """
        Move processed CSV to archive directory.

        Args:
            csv_path: Path to CSV file to archive
            archive_dir: Directory to archive to (default: data/processed/)

        Returns:
            Path to archived file
        """
        if archive_dir is None:
            archive_dir = self.data_dir / 'processed'

        # Create archive directory with date subdirectory
        date_dir = archive_dir / datetime.now().strftime("%Y-%m")
        date_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique archive name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{timestamp}_{csv_path.name}"
        archive_path = date_dir / archive_name

        try:
            csv_path.rename(archive_path)
            logger.info(f"Archived CSV: {csv_path.name} -> {archive_path}")
            return archive_path
        except Exception as e:
            logger.error(f"Error archiving CSV {csv_path}: {e}")
            return csv_path

    def parse_enhanced_csv(self, csv_path: Path) -> List[Dict]:
        """
        Parse Amazon CSV with enhanced item details for better YNAB memos.

        Args:
            csv_path: Path to CSV file

        Returns:
            List of order dictionaries with detailed item information
        """
        orders = {}  # Group by order ID

        try:
            # Handle BOM in CSV files
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    order_id = row.get('Order ID', '')
                    if not order_id:
                        continue

                    # Parse date
                    order_date = self._parse_date(row.get('Order Date', ''))
                    if not order_date:
                        continue

                    # Create or get existing order
                    if order_id not in orders:
                        # Get payment method - handle Business format
                        payment = row.get('Payment Instrument Type', '')
                        if row.get('Payment Identifier'):
                            # For Business format, combine type and identifier
                            identifier = row.get('Payment Identifier', '').strip('=').strip('"')
                            payment = f"{payment} ending in {identifier}"

                        orders[order_id] = {
                            'order_id': order_id,
                            'date': order_date,
                            'total': 0.0,
                            'subtotal': 0.0,
                            'tax': 0.0,
                            'items': [],
                            'status': row.get('Order Status', 'Delivered'),
                            'payment_method': self._map_payment_method(payment),
                            'shipping_address': row.get('Seller City', row.get('Ship City', '')),
                            'carrier': row.get('Carrier Name & Tracking Number', ''),
                            # NEW: Track payment reference for split payment detection
                            'payment_reference_id': row.get('Payment Reference ID', ''),
                            'payment_date': self._parse_date(row.get('Payment Date', '')),
                            'payment_amount': self._parse_amount(row.get('Payment Amount', '0')),
                            'payment_references': []  # Will collect all unique payment IDs for this order
                        }

                    # Parse item details - handle both formats
                    item_total = self._parse_amount(
                        row.get('Item Net Total') or row.get('Item Total') or '0'
                    )
                    item_subtotal = self._parse_amount(
                        row.get('Item Subtotal', '0')
                    )
                    item_tax = self._parse_amount(
                        row.get('Item Tax') or row.get('Order Tax') or '0'
                    )

                    # Add item to order
                    # Get ASIN from either column name
                    asin = self._extract_asin(row.get('ASIN') or row.get('ASIN/ISBN', ''))

                    item = {
                        'name': row.get('Title', 'Amazon Item'),
                        'category': row.get('Amazon-Internal Product Category') or row.get('Category', 'Shopping'),
                        'asin': asin,
                        'price': item_total,
                        'subtotal': item_subtotal,
                        'tax': item_tax,
                        'quantity': int(float(row.get('Item Quantity') or row.get('Quantity') or 1)),
                        'seller': row.get('Seller Name') or row.get('Seller', 'Amazon'),
                        'condition': row.get('Product Condition') or row.get('Condition', 'New'),
                        'link': f"https://www.amazon.com/dp/{asin}" if asin else ''
                    }

                    orders[order_id]['items'].append(item)
                    orders[order_id]['total'] += item_total
                    orders[order_id]['subtotal'] += item_subtotal
                    orders[order_id]['tax'] += item_tax

                    # Collect unique payment reference IDs to detect split payments
                    payment_ref = row.get('Payment Reference ID', '')
                    if payment_ref and payment_ref not in orders[order_id]['payment_references']:
                        orders[order_id]['payment_references'].append(payment_ref)

            # Post-process orders to detect split payments
            for order_id, order in orders.items():
                # If order has multiple payment references, it was split into multiple charges
                if len(order['payment_references']) > 1:
                    logger.info(f"Order {order_id} has {len(order['payment_references'])} split payments")
                    order['is_split_payment'] = True
                else:
                    order['is_split_payment'] = False

            # Convert to list
            order_list = list(orders.values())
            logger.info(f"Parsed {len(order_list)} orders with {sum(len(o['items']) for o in order_list)} items")
            return order_list

        except Exception as e:
            logger.error(f"Failed to parse enhanced CSV: {str(e)}")
            return []


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