"""
Test suite for Downloads Monitor functionality.
"""

import unittest
import tempfile
import shutil
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.downloads_monitor import DownloadsMonitor
from src.amazon_csv_importer import AmazonCSVImporter


class TestDownloadsMonitor(unittest.TestCase):
    """Test the downloads monitor functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.downloads_dir = Path(self.test_dir) / "downloads"
        self.archive_dir = Path(self.test_dir) / "archive"
        self.state_file = Path(self.test_dir) / "state.json"

        self.downloads_dir.mkdir()
        self.archive_dir.mkdir()

        # Initialize monitor
        self.monitor = DownloadsMonitor(
            downloads_dir=str(self.downloads_dir),
            archive_dir=str(self.archive_dir),
            state_file=str(self.state_file)
        )

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def create_amazon_csv(self, filename: str, num_orders: int = 3) -> Path:
        """Create a sample Amazon CSV file for testing."""
        csv_path = self.downloads_dir / filename

        headers = [
            'Order Date', 'Order ID', 'Title', 'Category',
            'ASIN/ISBN', 'Condition', 'Seller',
            'List Price Per Unit', 'Purchase Price Per Unit',
            'Quantity', 'Payment Instrument Type',
            'Purchase Order Number', 'PO Line Number',
            'Ordering Customer Email', 'Shipment Date',
            'Shipping Address Name', 'Shipping Address Street 1',
            'Shipping Address Street 2', 'Shipping Address City',
            'Shipping Address State', 'Shipping Address Zip',
            'Order Status', 'Carrier Name & Tracking Number',
            'Item Subtotal', 'Item Tax', 'Item Total'
        ]

        rows = []
        base_date = datetime.now() - timedelta(days=10)

        for i in range(num_orders):
            order_date = base_date + timedelta(days=i)
            rows.append({
                'Order Date': order_date.strftime('%m/%d/%Y'),
                'Order ID': f'111-{1234567890 + i:07d}-{1234567 + i:07d}',
                'Title': f'Test Product {i+1}',
                'Category': 'Electronics',
                'ASIN/ISBN': f'B00TEST{i:04d}',
                'Condition': 'New',
                'Seller': 'Amazon.com',
                'List Price Per Unit': '49.99',
                'Purchase Price Per Unit': '39.99',
                'Quantity': '1',
                'Payment Instrument Type': 'Visa ending in 1234',
                'Item Subtotal': '39.99',
                'Item Tax': '3.20',
                'Item Total': '43.19',
                'Order Status': 'Shipped',
                'Shipping Address City': 'Test City'
            })

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        return csv_path

    def test_find_amazon_csv_files(self):
        """Test finding Amazon CSV files in downloads folder."""
        # Create test CSV files
        self.create_amazon_csv('amazon_orders_2024.csv')
        self.create_amazon_csv('Order_History.csv')
        self.create_amazon_csv('random_file.csv')  # Should not match

        # Find CSV files
        csv_files = self.monitor.find_amazon_csv_files()

        # Should find 2 Amazon CSV files
        self.assertEqual(len(csv_files), 2)

        # Check that the right files were found
        filenames = [f.name for f in csv_files]
        self.assertIn('amazon_orders_2024.csv', filenames)
        self.assertIn('Order_History.csv', filenames)
        self.assertNotIn('random_file.csv', filenames)

    def test_get_latest_unprocessed_csv(self):
        """Test getting the latest unprocessed CSV file."""
        # Create test CSV files with different timestamps
        csv1 = self.create_amazon_csv('amazon_old.csv')
        csv2 = self.create_amazon_csv('amazon_new.csv')

        # Touch csv2 to make it newer
        import time
        time.sleep(0.1)
        csv2.touch()

        # Get latest unprocessed
        latest = self.monitor.get_latest_unprocessed_csv()

        self.assertIsNotNone(latest)
        self.assertEqual(latest.name, 'amazon_new.csv')

    def test_mark_as_processed(self):
        """Test marking a file as processed."""
        csv_path = self.create_amazon_csv('amazon_test.csv')

        # Mark as processed
        self.monitor.mark_as_processed(csv_path, transaction_count=5)

        # Should not be returned as unprocessed anymore
        latest = self.monitor.get_latest_unprocessed_csv()
        self.assertIsNone(latest)

        # Check state file
        with open(self.state_file, 'r') as f:
            state = json.load(f)

        self.assertIn('processed_files', state)
        self.assertEqual(len(state['processed_files']), 1)

        # Check that transaction count was recorded
        file_hash = self.monitor._get_file_hash(csv_path)
        self.assertEqual(state['processed_files'][file_hash]['transaction_count'], 5)

    def test_archive_file(self):
        """Test archiving a processed file."""
        csv_path = self.create_amazon_csv('amazon_to_archive.csv')

        # Archive the file
        archive_path = self.monitor.archive_file(csv_path)

        # Check that file was moved
        self.assertFalse(csv_path.exists())
        self.assertTrue(archive_path.exists())

        # Check archive location
        self.assertTrue(str(archive_path).startswith(str(self.archive_dir)))

    def test_file_hash_detection(self):
        """Test that identical files are detected by hash."""
        # Create a CSV file
        csv1 = self.create_amazon_csv('amazon1.csv', num_orders=5)

        # Mark as processed
        self.monitor.mark_as_processed(csv1, transaction_count=5)

        # Create another file with same content
        csv2_content = csv1.read_text()
        csv2 = self.downloads_dir / 'amazon2.csv'
        csv2.write_text(csv2_content)

        # Should detect as already processed (same hash)
        latest = self.monitor.get_latest_unprocessed_csv()
        self.assertIsNone(latest)  # Both files have same content, so both are "processed"

    def test_processing_stats(self):
        """Test getting processing statistics."""
        # Process some files
        csv1 = self.create_amazon_csv('amazon1.csv')
        csv2 = self.create_amazon_csv('amazon2.csv')

        self.monitor.mark_as_processed(csv1, transaction_count=10)
        self.monitor.mark_as_processed(csv2, transaction_count=15)

        # Get stats
        stats = self.monitor.get_processing_stats()

        self.assertEqual(stats['total_files'], 2)
        self.assertEqual(stats['total_transactions'], 25)
        self.assertIsNotNone(stats['last_processed'])
        self.assertEqual(len(stats['files']), 2)


class TestAmazonCSVImporterWithDownloads(unittest.TestCase):
    """Test the Amazon CSV importer with downloads folder support."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.downloads_dir = Path(self.test_dir) / "downloads"
        self.data_dir = Path(self.test_dir) / "data"

        self.downloads_dir.mkdir()
        self.data_dir.mkdir()

        # Initialize importer
        self.importer = AmazonCSVImporter(downloads_dir=str(self.downloads_dir))
        self.importer.data_dir = self.data_dir

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def create_amazon_csv(self, filename: str) -> Path:
        """Create a sample Amazon CSV file."""
        csv_path = self.downloads_dir / filename

        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Order Date', 'Order ID', 'Title', 'Category',
                'ASIN/ISBN', 'Quantity', 'Item Total',
                'Payment Instrument Type', 'Order Status'
            ])
            writer.writerow([
                '11/01/2024', '111-1234567-1234567',
                'Echo Dot (5th Gen)', 'Electronics',
                'B09B8V1LZ3', '1', '49.99',
                'Amazon Business Prime Card', 'Delivered'
            ])
            writer.writerow([
                '11/02/2024', '111-2345678-2345678',
                'USB-C Cable 2-Pack', 'Electronics',
                'B07TZK1234', '2', '15.99',
                'Chase Reserve CC', 'Delivered'
            ])

        return csv_path

    def test_find_latest_amazon_csv(self):
        """Test finding the latest Amazon CSV in downloads folder."""
        # Create test CSV files
        csv1 = self.create_amazon_csv('amazon_old.csv')
        csv2 = self.create_amazon_csv('amazon_new.csv')

        # Make csv2 newer
        import time
        time.sleep(0.1)
        csv2.touch()

        # Find latest
        latest = self.importer.find_latest_amazon_csv()

        self.assertIsNotNone(latest)
        self.assertEqual(latest.name, 'amazon_new.csv')

    def test_import_from_downloads(self):
        """Test importing orders from downloads folder."""
        # Create test CSV
        self.create_amazon_csv('amazon_orders.csv')

        # Import from downloads
        orders, csv_path = self.importer.import_from_downloads()

        self.assertIsNotNone(csv_path)
        self.assertEqual(len(orders), 2)

        # Check first order
        self.assertEqual(orders[0]['order_id'], '111-1234567-1234567')
        self.assertEqual(orders[0]['total'], 49.99)
        self.assertEqual(orders[0]['items'][0]['name'], 'Echo Dot (5th Gen)')

        # Check that file was marked as processed
        orders2, csv_path2 = self.importer.import_from_downloads()
        self.assertEqual(len(orders2), 0)  # Should be empty - already processed
        self.assertIsNone(csv_path2)

    def test_is_amazon_csv(self):
        """Test detection of Amazon CSV files by headers."""
        # Create a valid Amazon CSV
        amazon_csv = self.downloads_dir / 'amazon.csv'
        with open(amazon_csv, 'w') as f:
            f.write('Order Date,Order ID,Title,Category,Item Total\n')
            f.write('11/01/2024,111-1234567,Product,Electronics,49.99\n')

        # Create a non-Amazon CSV
        other_csv = self.downloads_dir / 'other.csv'
        with open(other_csv, 'w') as f:
            f.write('Date,Name,Amount\n')
            f.write('2024-11-01,John Doe,100.00\n')

        # Test detection
        self.assertTrue(self.importer._is_amazon_csv(amazon_csv))
        self.assertFalse(self.importer._is_amazon_csv(other_csv))

    def test_parse_enhanced_csv(self):
        """Test parsing CSV with enhanced item details."""
        # Create detailed CSV
        csv_path = self.downloads_dir / 'detailed.csv'
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Order Date', 'Order ID', 'Title', 'Category',
                'ASIN/ISBN', 'Quantity', 'Item Total', 'Item Subtotal',
                'Item Tax', 'Seller', 'Condition',
                'Payment Instrument Type', 'Order Status', 'Ship City'
            ])
            # Order with multiple items (same order ID)
            writer.writerow([
                '11/01/2024', '111-1234567-1234567',
                'Echo Dot', 'Electronics', 'B09B8V1LZ3',
                '1', '49.99', '45.99', '4.00',
                'Amazon', 'New', 'Visa', 'Delivered', 'New York'
            ])
            writer.writerow([
                '11/01/2024', '111-1234567-1234567',
                'Echo Dot Case', 'Electronics', 'B09B8VCASE',
                '1', '19.99', '18.49', '1.50',
                'Third Party', 'New', 'Visa', 'Delivered', 'New York'
            ])

        # Parse the CSV
        orders = self.importer.parse_enhanced_csv(csv_path)

        self.assertEqual(len(orders), 1)  # One order
        self.assertEqual(len(orders[0]['items']), 2)  # Two items

        # Check order details
        order = orders[0]
        self.assertEqual(order['order_id'], '111-1234567-1234567')
        self.assertEqual(order['total'], 69.98)  # Sum of both items
        self.assertEqual(order['tax'], 5.50)  # Sum of taxes
        self.assertEqual(order['shipping_address'], 'New York')

        # Check items
        self.assertEqual(order['items'][0]['name'], 'Echo Dot')
        self.assertEqual(order['items'][0]['seller'], 'Amazon')
        self.assertEqual(order['items'][1]['name'], 'Echo Dot Case')
        self.assertEqual(order['items'][1]['seller'], 'Third Party')


if __name__ == '__main__':
    unittest.main()