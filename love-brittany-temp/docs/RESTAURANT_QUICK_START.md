# Restaurant Discovery - Quick Start Guide

Get your Atlanta date night restaurant discovery system up and running in 5 minutes!

## What You're Getting

✅ **20 curated top Atlanta restaurants** with detailed info
✅ **One-click reservation booking** via OpenTable, Tock, Resy
✅ **Automatic visit tracking** from your Google Calendar
✅ **Beautiful web interface** - mobile responsive
✅ **Email integration** - button in your bi-weekly reports

## Step 1: Test Locally (2 minutes)

```bash
# Navigate to the project
cd ~/personal-workspace-1/projects/Life\ Automations/relationship-tracker

# Start the app
./run_restaurant_app.sh
```

Open your browser to: **http://localhost:5000**

You should see:
- 20 Atlanta restaurants
- Beautiful gradient purple design
- Stats showing total/visited/new restaurants
- Each restaurant card with booking button

## Step 2: Deploy to Render (5 minutes - FREE)

### Why Render?
- ✅ **100% Free** forever
- ✅ **Automatic HTTPS** (secure)
- ✅ **Zero configuration** needed
- ✅ **Auto-deploys** when you push to GitHub
- ❗ Sleeps after 15 min of inactivity (30 sec to wake up)

### Deploy Steps:

1. **Create Render account:**
   - Go to https://render.com/
   - Click "Get Started for Free"
   - Sign up with GitHub

2. **Create new Web Service:**
   - Click "New +" in top right
   - Select "Web Service"
   - Click "Connect GitHub"
   - Select your `personal-workspace-1` repository
   - Click "Connect"

3. **Configure the service:**
   ```
   Name: atlanta-date-restaurants
   Region: Oregon (or closest to you)
   Branch: main
   Root Directory: projects/Life Automations/relationship-tracker
   Runtime: Python 3
   Build Command: pip install -r requirements-web.txt
   Start Command: gunicorn -w 2 -b 0.0.0.0:$PORT src.restaurant_web_app:app
   Instance Type: Free
   ```

4. **Add environment variables:**

   Click "Advanced" → "Add Environment Variable"

   You'll need to add your Google credentials. The easiest way:

   ```bash
   # In your terminal, get the credentials:
   cat ~/personal-workspace-1/projects/Life\ Automations/tokens/credentials.json
   ```

   Add these variables:
   - Key: `GOOGLE_APPLICATION_CREDENTIALS`
   - Value: `/etc/secrets/credentials.json` (we'll upload the file separately)

5. **Deploy:**
   - Click "Create Web Service"
   - Wait 2-3 minutes for first deploy
   - You'll get a URL like: `https://atlanta-date-restaurants.onrender.com`

6. **Update your config:**

   Edit `config.yaml`:
   ```yaml
   restaurant_page_url: "https://atlanta-date-restaurants.onrender.com"
   ```

## Step 3: Test the Email Button

```bash
# Generate a test report
cd ~/personal-workspace-1/projects/Life\ Automations/relationship-tracker
../venv/bin/python src/relationship_main.py
```

Check your email - you should see a purple gradient button that says:
**"🍽️ Discover Atlanta Restaurants for Date Night"**

Click it to open your deployed restaurant page!

## Common Issues

### "ModuleNotFoundError: No module named 'flask'"

```bash
pip install -r requirements-web.txt
```

### "Permission denied: ./run_restaurant_app.sh"

```bash
chmod +x run_restaurant_app.sh
```

### "Can't connect to Google Calendar"

Make sure you have:
1. Google Calendar API enabled
2. credentials.json in the tokens/ folder
3. Proper authentication set up (run the main tracker once)

### Restaurants not showing as visited

The system looks for these keywords in calendar events:
- "date night"
- "dinner"
- "restaurant"
- "reservation"

Make sure your past date night events include:
- Restaurant name in the event title OR
- Restaurant name in the event description

Example: "Date Night at Atlas" or "Dinner - Canoe"

## What's Next?

### Customize Your Restaurants

Edit `src/restaurant_web_app.py` - the `ATLANTA_RESTAURANTS` list:

```python
ATLANTA_RESTAURANTS = [
    {
        'id': 1,
        'name': 'Your Favorite Restaurant',
        'cuisine': 'Cuisine Type',
        # ... add your own!
    }
]
```

### Keep Your Visit History Updated

Just add restaurant names to your date night calendar events:
- "Date Night at [Restaurant Name]"
- Put restaurant name in event description
- Use keywords: dinner, reservation, date

The system auto-updates every time you visit the page!

### Share With Your Partner

Send them the URL - it works perfectly on mobile!

---

**Questions?** Check the full guide: `docs/RESTAURANT_DISCOVERY_GUIDE.md`

**Enjoy discovering amazing Atlanta restaurants!** 🍽️💕
