"""
Atlanta Date Night Restaurant Discovery Web Application

Features:
- Curated list of top Atlanta restaurants
- Auto-updates to show visited restaurants (past 12 months)
- Direct reservation booking links
- Beautiful, mobile-responsive interface
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / 'shared' / 'src'))

from calendar_service import CalendarService

logger = logging.getLogger(__name__)

# Configure Flask app with proper template directory
template_dir = Path(__file__).parent.parent / 'templates'
app = Flask(__name__, template_folder=str(template_dir))

# Top Atlanta Restaurants Database
ATLANTA_RESTAURANTS = [
    {
        'id': 1,
        'name': 'Atlas',
        'cuisine': 'American Fine Dining',
        'neighborhood': 'St. Regis Atlanta',
        'description': 'Stunning art deco dining room with elevated American cuisine and craft cocktails.',
        'price_range': '$$$$',
        'reservation_link': 'https://www.opentable.com/r/atlas-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.atlas-restaurant.com',
        'phone': '(404) 800-5995',
        'dress_code': 'Smart Casual',
        'best_for': ['Anniversary', 'Special Occasion', 'Romantic']
    },
    {
        'id': 2,
        'name': 'Canoe',
        'cuisine': 'Contemporary American',
        'neighborhood': 'Vinings',
        'description': 'Riverside fine dining with seasonal Southern-inspired cuisine and romantic patio.',
        'price_range': '$$$',
        'reservation_link': 'https://www.opentable.com/r/canoe-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.canoeatl.com',
        'phone': '(770) 432-2663',
        'dress_code': 'Business Casual',
        'best_for': ['Romantic', 'Waterfront', 'Special Occasion']
    },
    {
        'id': 3,
        'name': 'Bacchanalia',
        'cuisine': 'Contemporary American',
        'neighborhood': 'Westside',
        'description': 'Upscale organic farm-to-table dining with prix fixe menu and urban garden.',
        'price_range': '$$$$',
        'reservation_link': 'https://www.exploretock.com/bacchanalia',
        'reservation_platform': 'Tock',
        'website': 'https://www.starprovisions.com/bacchanalia',
        'phone': '(404) 365-0410',
        'dress_code': 'Smart Casual',
        'best_for': ['Fine Dining', 'Farm-to-Table', 'Anniversary']
    },
    {
        'id': 4,
        'name': 'The Optimist',
        'cuisine': 'Seafood',
        'neighborhood': 'Westside',
        'description': 'Coastal seafood hall with oyster bar, wood-fired fish, and lively atmosphere.',
        'price_range': '$$$',
        'reservation_link': 'https://www.opentable.com/r/the-optimist-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://theoptimistrestaurant.com',
        'phone': '(404) 477-6260',
        'dress_code': 'Casual',
        'best_for': ['Seafood', 'Lively', 'Group Dining']
    },
    {
        'id': 5,
        'name': 'Staplehouse',
        'cuisine': 'New American',
        'neighborhood': 'Old Fourth Ward',
        'description': 'Intimate tasting menu restaurant with creative seasonal dishes and cozy ambiance.',
        'price_range': '$$$$',
        'reservation_link': 'https://www.exploretock.com/staplehouse',
        'reservation_platform': 'Tock',
        'website': 'https://www.staplehouse.com',
        'phone': '(404) 524-5005',
        'dress_code': 'Smart Casual',
        'best_for': ['Tasting Menu', 'Intimate', 'Romantic']
    },
    {
        'id': 6,
        'name': 'Gunshow',
        'cuisine': 'International',
        'neighborhood': 'Glenwood Park',
        'description': 'Unique dim sum-style experience where chefs present dishes tableside.',
        'price_range': '$$$',
        'reservation_link': 'https://www.opentable.com/r/gunshow-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.gunshowatl.com',
        'phone': '(404) 380-1886',
        'dress_code': 'Casual',
        'best_for': ['Unique Experience', 'Interactive', 'Fun']
    },
    {
        'id': 7,
        'name': 'Le Bilboquet',
        'cuisine': 'French',
        'neighborhood': 'Buckhead',
        'description': 'Classic French brasserie with timeless dishes and sophisticated atmosphere.',
        'price_range': '$$$$',
        'reservation_link': 'https://www.opentable.com/r/le-bilboquet-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.lebilboquetatlanta.com',
        'phone': '(404) 600-0645',
        'dress_code': 'Smart Casual',
        'best_for': ['French Cuisine', 'Elegant', 'Date Night']
    },
    {
        'id': 8,
        'name': 'Hal\'s',
        'cuisine': 'Steakhouse',
        'neighborhood': 'Buckhead',
        'description': 'Upscale steakhouse with prime cuts, raw bar, and classic cocktails.',
        'price_range': '$$$$',
        'reservation_link': 'https://www.opentable.com/r/hals-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.halsatlanta.com',
        'phone': '(404) 425-9990',
        'dress_code': 'Business Casual',
        'best_for': ['Steakhouse', 'Special Occasion', 'Classic']
    },
    {
        'id': 9,
        'name': 'Bones',
        'cuisine': 'Steakhouse',
        'neighborhood': 'Buckhead',
        'description': 'Legendary Atlanta steakhouse known for impeccable service and prime beef.',
        'price_range': '$$$$',
        'reservation_link': 'https://www.opentable.com/r/bones-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.bonesrestaurant.com',
        'phone': '(404) 237-2663',
        'dress_code': 'Business Casual',
        'best_for': ['Steakhouse', 'Business Dining', 'Classic']
    },
    {
        'id': 10,
        'name': 'Aria',
        'cuisine': 'New American',
        'neighborhood': 'Buckhead',
        'description': 'Modern American fine dining with seasonal tasting menus and extensive wine list.',
        'price_range': '$$$$',
        'reservation_link': 'https://www.opentable.com/r/aria-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.aria-atl.com',
        'phone': '(404) 233-7673',
        'dress_code': 'Smart Casual',
        'best_for': ['Fine Dining', 'Romantic', 'Wine Pairing']
    },
    {
        'id': 11,
        'name': 'Marcel',
        'cuisine': 'Steakhouse',
        'neighborhood': 'Westside',
        'description': 'Elegant steakhouse with French influences and sophisticated cocktails.',
        'price_range': '$$$$',
        'reservation_link': 'https://www.opentable.com/r/marcel-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.marcelsteakhouse.com',
        'phone': '(404) 665-4555',
        'dress_code': 'Smart Casual',
        'best_for': ['Steakhouse', 'Date Night', 'French-Inspired']
    },
    {
        'id': 12,
        'name': 'Lazy Betty',
        'cuisine': 'Contemporary',
        'neighborhood': 'Candler Park',
        'description': 'Intimate tasting menu experience with inventive dishes and impeccable service.',
        'price_range': '$$$$',
        'reservation_link': 'https://www.exploretock.com/lazybetty',
        'reservation_platform': 'Tock',
        'website': 'https://www.lazybettyatl.com',
        'phone': '(404) 600-7755',
        'dress_code': 'Smart Casual',
        'best_for': ['Tasting Menu', 'Special Occasion', 'Innovative']
    },
    {
        'id': 13,
        'name': 'Serpas True Food',
        'cuisine': 'Louisiana Creole',
        'neighborhood': 'Old Fourth Ward',
        'description': 'Vibrant Creole cuisine with Louisiana flavors and Southern hospitality.',
        'price_range': '$$',
        'reservation_link': 'https://www.opentable.com/r/serpas-true-food-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.serpastruefood.com',
        'phone': '(404) 525-5515',
        'dress_code': 'Casual',
        'best_for': ['Creole', 'Lively', 'Flavorful']
    },
    {
        'id': 14,
        'name': 'Ponce City Market (Various)',
        'cuisine': 'Food Hall',
        'neighborhood': 'Ponce City Market',
        'description': 'Upscale food hall with diverse dining options and rooftop views.',
        'price_range': '$$',
        'reservation_link': 'https://www.poncecitymarket.com/dine',
        'reservation_platform': 'Various',
        'website': 'https://www.poncecitymarket.com',
        'phone': '(404) 900-7900',
        'dress_code': 'Casual',
        'best_for': ['Variety', 'Casual', 'Rooftop']
    },
    {
        'id': 15,
        'name': 'St. Cecilia',
        'cuisine': 'Italian',
        'neighborhood': 'Buckhead',
        'description': 'Coastal Italian cuisine with wood-fired dishes and elegant ambiance.',
        'price_range': '$$$',
        'reservation_link': 'https://www.opentable.com/r/st-cecilia-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://stceciliaatl.com',
        'phone': '(404) 620-4800',
        'dress_code': 'Smart Casual',
        'best_for': ['Italian', 'Romantic', 'Date Night']
    },
    {
        'id': 16,
        'name': 'Chops Lobster Bar',
        'cuisine': 'Steakhouse & Seafood',
        'neighborhood': 'Buckhead',
        'description': 'Upscale steakhouse and lobster bar with classic cocktails.',
        'price_range': '$$$$',
        'reservation_link': 'https://www.opentable.com/r/chops-lobster-bar-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.buckheadrestaurants.com/chops-lobster-bar',
        'phone': '(404) 262-2675',
        'dress_code': 'Business Casual',
        'best_for': ['Steakhouse', 'Seafood', 'Classic']
    },
    {
        'id': 17,
        'name': 'The Garden Room',
        'cuisine': 'New American',
        'neighborhood': 'Buckhead',
        'description': 'Garden-inspired dining with seasonal menu and beautiful greenhouse setting.',
        'price_range': '$$$',
        'reservation_link': 'https://www.opentable.com/r/the-garden-room-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://thegardenroomatl.com',
        'phone': '(404) 549-9788',
        'dress_code': 'Smart Casual',
        'best_for': ['Romantic', 'Garden Setting', 'Instagram-worthy']
    },
    {
        'id': 18,
        'name': 'Nan Thai Fine Dining',
        'cuisine': 'Thai',
        'neighborhood': 'Midtown',
        'description': 'Upscale Thai cuisine with authentic flavors and elegant presentation.',
        'price_range': '$$$',
        'reservation_link': 'https://www.opentable.com/r/nan-thai-fine-dining-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://www.nanthaiatl.com',
        'phone': '(404) 870-9933',
        'dress_code': 'Casual',
        'best_for': ['Thai', 'Authentic', 'Unique']
    },
    {
        'id': 19,
        'name': 'Kimball House',
        'cuisine': 'American',
        'neighborhood': 'Decatur',
        'description': 'Oyster bar and seasonal American fare in a historic renovated building.',
        'price_range': '$$',
        'reservation_link': 'https://www.exploretock.com/kimballhouse',
        'reservation_platform': 'Tock',
        'website': 'https://kimball-house.com',
        'phone': '(404) 378-3502',
        'dress_code': 'Casual',
        'best_for': ['Oysters', 'Historic', 'Cocktails']
    },
    {
        'id': 20,
        'name': 'Miller Union',
        'cuisine': 'Southern',
        'neighborhood': 'Westside',
        'description': 'Farm-to-table Southern cuisine with rotating seasonal menu.',
        'price_range': '$$$',
        'reservation_link': 'https://www.opentable.com/r/miller-union-atlanta',
        'reservation_platform': 'OpenTable',
        'website': 'https://millerunion.com',
        'phone': '(678) 733-8550',
        'dress_code': 'Casual',
        'best_for': ['Southern', 'Farm-to-Table', 'Local']
    }
]


class RestaurantService:
    """Service for managing restaurant data and visit tracking."""

    def __init__(self, calendar_service: CalendarService):
        self.calendar_service = calendar_service

    def get_all_restaurants(self):
        """Get all restaurants."""
        return ATLANTA_RESTAURANTS

    def get_visited_restaurants(self, months_back=12):
        """
        Get list of restaurants visited in the past X months.

        Args:
            months_back: Number of months to look back (default: 12)

        Returns:
            Set of restaurant names that have been visited
        """
        logger.info(f"Checking for visited restaurants in past {months_back} months...")

        now = datetime.now()
        start_date = now - timedelta(days=months_back * 30)

        # Get all calendar events that might be restaurant visits
        events = self.calendar_service.get_events(
            start_date=start_date,
            end_date=now,
            search_terms=['date night', 'dinner', 'restaurant', 'date', 'reservation']
        )

        visited = set()

        # Check if any restaurant names appear in event titles or descriptions
        for event in events:
            event_text = f"{event.get('summary', '')} {event.get('description', '')}".lower()

            for restaurant in ATLANTA_RESTAURANTS:
                restaurant_name = restaurant['name'].lower()
                # Check for restaurant name in event
                if restaurant_name in event_text:
                    visited.add(restaurant['name'])
                    logger.info(f"Found visit to {restaurant['name']} on {event['start']}")

        logger.info(f"Found {len(visited)} visited restaurants")
        return visited

    def get_restaurants_with_visit_status(self, months_back=12):
        """
        Get all restaurants with visit status.

        Returns:
            List of restaurants with 'visited' flag
        """
        visited_names = self.get_visited_restaurants(months_back)

        restaurants_with_status = []
        for restaurant in ATLANTA_RESTAURANTS:
            restaurant_copy = restaurant.copy()
            restaurant_copy['visited'] = restaurant['name'] in visited_names
            restaurants_with_status.append(restaurant_copy)

        # Sort: unvisited first, then by name
        restaurants_with_status.sort(key=lambda r: (r['visited'], r['name']))

        return restaurants_with_status


# Flask Routes

@app.route('/')
def index():
    """Render the main restaurant listing page."""
    return render_template('restaurants.html')


@app.route('/api/restaurants')
def get_restaurants():
    """API endpoint to get restaurants with visit status."""
    try:
        # Try to initialize calendar service for visit tracking
        restaurants_with_status = []

        try:
            # Initialize calendar service
            config_path = Path(__file__).parent.parent.parent / 'config.yaml'
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Load environment variables for calendar service
            env_path = Path(__file__).parent.parent.parent / '.env'
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()

            calendar_service = CalendarService()
            restaurant_service = RestaurantService(calendar_service)
            restaurants_with_status = restaurant_service.get_restaurants_with_visit_status()

        except Exception as calendar_error:
            logger.warning(f"Calendar service unavailable, showing all restaurants as new: {calendar_error}")
            # If calendar service fails, return all restaurants as unvisited
            restaurants_with_status = []
            for restaurant in ATLANTA_RESTAURANTS:
                restaurant_copy = restaurant.copy()
                restaurant_copy['visited'] = False
                restaurants_with_status.append(restaurant_copy)

        return jsonify({
            'success': True,
            'restaurants': restaurants_with_status,
            'total': len(restaurants_with_status),
            'visited_count': sum(1 for r in restaurants_with_status if r['visited'])
        })

    except Exception as e:
        logger.error(f"Error fetching restaurants: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/restaurants/<int:restaurant_id>')
def get_restaurant_details(restaurant_id):
    """Get details for a specific restaurant."""
    restaurant = next((r for r in ATLANTA_RESTAURANTS if r['id'] == restaurant_id), None)

    if not restaurant:
        return jsonify({'success': False, 'error': 'Restaurant not found'}), 404

    return jsonify({'success': True, 'restaurant': restaurant})


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
