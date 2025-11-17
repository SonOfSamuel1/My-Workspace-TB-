# Atlanta Date Night Restaurant Discovery System

## Overview

An interactive web application that helps you discover and book the best restaurants in Atlanta for date nights. The system automatically tracks which restaurants you've visited in the past 12 months and provides one-click access to make reservations.

## Features

### 🍽️ Curated Restaurant Database
- **20 top-rated Atlanta restaurants** across various cuisines and price points
- Detailed information including:
  - Cuisine type and neighborhood
  - Price range and dress code
  - Restaurant description
  - Best suited occasions (romantic, special occasion, etc.)
  - Contact information

### 📅 Automatic Visit Tracking
- Integrates with your Google Calendar
- Automatically detects restaurant visits from calendar events
- Shows which restaurants you've been to in the past 12 months
- Highlights new restaurants to try

### 🔗 One-Click Reservations
- Direct links to reservation platforms (OpenTable, Tock, Resy)
- Click "Book on [Platform]" to go straight to the reservation page
- Website links for additional information
- Phone numbers for direct booking

### 📧 Email Integration
- Beautiful button in your bi-weekly Love Brittany Action Plan reports
- One-click access from email to restaurant discovery page
- Mobile-responsive design

## Quick Start

### Local Development

1. **Start the application:**
   ```bash
   cd relationship-tracker
   ./run_restaurant_app.sh
   ```

2. **Open your browser:**
   ```
   http://localhost:5000
   ```

3. **Browse restaurants:**
   - View all 20 curated restaurants
   - Filter by "New to Try" or "Previously Visited"
   - Click reservation buttons to book

### Configuration

Update `config.yaml` to set your restaurant page URL:

```yaml
relationship_tracking:
  # URL for the restaurant discovery page
  # Use localhost for local testing, or your deployed URL
  restaurant_page_url: "http://localhost:5000"
  # After deployment, change to your public URL:
  # restaurant_page_url: "https://your-domain.com"
```

## Deployment Options

### Option 1: Render (Free Tier - Recommended)

**Pros:** Free, automatic HTTPS, easy deployment
**Cons:** App sleeps after inactivity (30 sec cold start)

1. **Create Render account:**
   - Go to https://render.com
   - Sign up with GitHub

2. **Create new Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select this project

3. **Configure service:**
   ```
   Name: atlanta-date-restaurants
   Environment: Python 3
   Build Command: pip install -r relationship-tracker/requirements-web.txt
   Start Command: cd relationship-tracker && gunicorn -w 2 -b 0.0.0.0:$PORT src.restaurant_web_app:app
   ```

4. **Add environment variables:**
   - Add your Google credentials
   - Copy from your local `.env` file

5. **Deploy:**
   - Click "Create Web Service"
   - Wait 2-3 minutes for deployment
   - Your URL will be: `https://atlanta-date-restaurants.onrender.com`

6. **Update config.yaml:**
   ```yaml
   restaurant_page_url: "https://atlanta-date-restaurants.onrender.com"
   ```

### Option 2: Heroku (Free Tier)

1. **Install Heroku CLI:**
   ```bash
   brew install heroku/brew/heroku
   ```

2. **Create Heroku app:**
   ```bash
   cd relationship-tracker
   heroku create atlanta-date-restaurants
   ```

3. **Create Procfile:**
   ```
   web: cd relationship-tracker && gunicorn src.restaurant_web_app:app
   ```

4. **Deploy:**
   ```bash
   git push heroku main
   ```

5. **Set environment variables:**
   ```bash
   heroku config:set GOOGLE_CREDENTIALS="$(cat tokens/credentials.json)"
   ```

### Option 3: PythonAnywhere (Free Tier)

1. **Create account:** https://www.pythonanywhere.com
2. **Upload code** via web interface or Git
3. **Create new web app** with Flask
4. **Set working directory** to relationship-tracker
5. **Configure WSGI file** to import the app

### Option 4: Local Network Access (Free)

If you just want to access it from your local network:

1. **Find your local IP:**
   ```bash
   ifconfig | grep "inet "
   ```

2. **Run with network access:**
   ```bash
   cd relationship-tracker/src
   python restaurant_web_app.py --host=0.0.0.0
   ```

3. **Access from any device on your network:**
   ```
   http://192.168.1.X:5000  (use your IP)
   ```

## Restaurant Database

### Current Restaurants (20)

**Fine Dining ($$$-$$$$):**
- Atlas - Art deco American fine dining
- Bacchanalia - Organic farm-to-table
- Aria - Modern American with tasting menu
- Lazy Betty - Contemporary tasting menu
- Staplehouse - Intimate new American

**Steakhouses ($$$$):**
- Hal's - Upscale with raw bar
- Bones - Legendary Atlanta classic
- Marcel - French-inspired elegance
- Chops Lobster Bar - Steakhouse & seafood

**International:**
- Le Bilboquet - Classic French brasserie
- Nan Thai Fine Dining - Upscale Thai
- St. Cecilia - Coastal Italian
- Serpas True Food - Louisiana Creole

**Seafood:**
- The Optimist - Coastal seafood hall
- Canoe - Riverside fine dining

**Unique Experiences:**
- Gunshow - Interactive dim sum-style
- The Garden Room - Greenhouse setting
- Kimball House - Historic oyster bar

**Casual:**
- Miller Union - Farm-to-table Southern
- Ponce City Market - Upscale food hall

### Adding New Restaurants

Edit `src/restaurant_web_app.py` and add to the `ATLANTA_RESTAURANTS` list:

```python
{
    'id': 21,  # Increment ID
    'name': 'Restaurant Name',
    'cuisine': 'Cuisine Type',
    'neighborhood': 'Neighborhood',
    'description': 'Brief description of the restaurant',
    'price_range': '$$',  # $-$$$$
    'reservation_link': 'https://opentable.com/...',
    'reservation_platform': 'OpenTable',  # or Tock, Resy
    'website': 'https://...',
    'phone': '(404) 123-4567',
    'dress_code': 'Casual',  # Casual, Business Casual, Smart Casual
    'best_for': ['Tags', 'Here']  # e.g., Romantic, Anniversary
}
```

## Visit Tracking

The system automatically tracks restaurant visits by:

1. Scanning your Google Calendar for the past 12 months
2. Looking for events with keywords: `date night`, `dinner`, `restaurant`, `reservation`
3. Matching restaurant names in event titles/descriptions
4. Marking restaurants as "Visited" with a green checkmark

### Tips for Accurate Tracking

**Include restaurant name in calendar events:**
```
✓ "Date Night at Atlas"
✓ "Dinner reservation - Canoe"
✓ "Atlas Restaurant 7pm"
```

**Or in event descriptions:**
```
Event: Date Night
Description: Reservation at Bacchanalia for 7:30pm
```

## Email Button Integration

Your bi-weekly Love Brittany Action Plan reports now include a prominent button in the Date Nights section:

**Button appearance:**
- Purple gradient background
- "🍽️ Discover Atlanta Restaurants for Date Night" text
- Subtitle: "Browse curated restaurants with one-click reservations • Auto-updates with your visit history"

**When clicked:**
- Opens the restaurant discovery page in a new tab
- Shows live data with current visit status
- Ready to book reservations immediately

## Customization

### Change Color Scheme

Edit `templates/restaurants.html` and modify the CSS:

```css
/* Header gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Button gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Accent color */
color: #e91e63;
```

### Change Port

Default port is 5000. To use a different port:

```bash
PORT=8080 python src/restaurant_web_app.py
```

### Add Search/Sorting

The frontend already includes filtering. To add search functionality, edit `templates/restaurants.html` and add a search input that filters by name/cuisine.

## Troubleshooting

### "No restaurants found"
- Check that your Google Calendar credentials are configured
- Verify `config.yaml` has correct settings
- Check logs for authentication errors

### Restaurants not marked as visited
- Ensure calendar events include restaurant names
- Check the 12-month lookback window
- Verify calendar service has proper permissions

### Button not appearing in email
- Check `config.yaml` has `restaurant_page_url` set
- Regenerate the email report
- Verify you're using the latest report generator

### App won't start
- Check virtual environment is activated
- Install dependencies: `pip install -r requirements-web.txt`
- Verify Python version (3.8+)

## Future Enhancements

Potential additions:
- [ ] Add more Atlanta restaurants (30-40 total)
- [ ] Filter by neighborhood
- [ ] Filter by cuisine type
- [ ] Sort by price range
- [ ] Add restaurant photos
- [ ] Track frequency of visits
- [ ] Suggest restaurants based on history
- [ ] Add rating/review integration
- [ ] Mobile app version
- [ ] Share restaurant list with partner

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs in `logs/`
3. Verify Google Calendar API permissions
4. Check configuration in `config.yaml`

---

**Enjoy discovering amazing Atlanta restaurants for your date nights!** 🍽️💕
