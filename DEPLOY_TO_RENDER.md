# Deploy Restaurant Discovery App to Render

## Step-by-Step Deployment Guide

### Prerequisites
- GitHub account with your code pushed
- Render account (free) - https://render.com

---

## Part 1: Prepare for Deployment (2 minutes)

### 1. Verify Files Are Ready

Check that these files exist:
```bash
cd ~/personal-workspace-1/projects/Life\ Automations/relationship-tracker
ls requirements-web.txt    # ✓ Should exist
ls render.yaml             # ✓ Should exist
ls src/restaurant_web_app.py  # ✓ Should exist
ls templates/restaurants.html # ✓ Should exist
```

### 2. Push to GitHub

```bash
cd ~/personal-workspace-1
git add .
git commit -m "Add restaurant discovery app for deployment"
git push origin main
```

---

## Part 2: Deploy on Render (5 minutes)

### Step 1: Create Render Account

1. Go to **https://render.com**
2. Click **"Get Started for Free"**
3. Sign up with **GitHub** (easiest option)
4. Authorize Render to access your repositories

### Step 2: Create New Web Service

1. Click **"New +"** in the top right
2. Select **"Web Service"**
3. Click **"Connect a repository"**
4. Find and select: **personal-workspace-1** (or your repo name)
5. Click **"Connect"**

### Step 3: Configure the Service

Fill in these exact settings:

**Basic Settings:**
```
Name: atlanta-date-restaurants
Region: Oregon (or closest to you)
Branch: main
Runtime: Python 3
```

**Build & Deploy:**
```
Root Directory: projects/Life Automations/relationship-tracker
Build Command: pip install -r requirements-web.txt
Start Command: gunicorn --workers 2 --bind 0.0.0.0:$PORT src.restaurant_web_app:app
```

**Instance Type:**
```
Select: Free
```

### Step 4: Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"

You need to add your Google credentials. There are 2 options:

#### Option A: Using Service Account (Recommended)

If you have a service account JSON:

1. Click "Add Secret File"
2. Filename: `credentials.json`
3. Contents: Paste your entire credentials.json content
4. Add environment variable:
   - Key: `GOOGLE_APPLICATION_CREDENTIALS`
   - Value: `/etc/secrets/credentials.json`

#### Option B: Using OAuth Credentials

Add these environment variables from your `.env` file:

```bash
# Get your current credentials
cat ~/personal-workspace-1/projects/Life\ Automations/.env
```

Add each one:
- `GOOGLE_CREDENTIALS_FILE`
- `GOOGLE_TOKEN_FILE`
- `GOOGLE_CALENDAR_ID`
- Any other required variables

### Step 5: Deploy

1. Click **"Create Web Service"** at the bottom
2. Wait 2-3 minutes for deployment
3. Watch the logs for any errors

### Step 6: Get Your URL

Once deployed, you'll see:
```
Your service is live at https://atlanta-date-restaurants.onrender.com
```

Copy this URL!

---

## Part 3: Update Configuration (1 minute)

### Update config.yaml

```bash
cd ~/personal-workspace-1/projects/Life\ Automations
```

Edit `config.yaml` and change:

```yaml
relationship_tracking:
  restaurant_page_url: "https://atlanta-date-restaurants.onrender.com"
```

### Commit and Push

```bash
git add config.yaml
git commit -m "Update restaurant page URL with Render deployment"
git push origin main
```

---

## Part 4: Test the Deployment (2 minutes)

### Test 1: Visit the URL

Open in browser:
```
https://atlanta-date-restaurants.onrender.com
```

You should see:
- ✅ Beautiful purple gradient header
- ✅ "Atlanta Date Night Restaurants" title
- ✅ Stats showing 20 restaurants
- ✅ Restaurant cards loading

### Test 2: Check API

Visit:
```
https://atlanta-date-restaurants.onrender.com/api/restaurants
```

You should see JSON with all restaurants.

### Test 3: Send New Email

```bash
cd ~/personal-workspace-1/projects/Life\ Automations/relationship-tracker
../venv/bin/python src/relationship_main.py --generate
```

Check your email - the button should now link to your Render URL!

---

## Troubleshooting

### Issue: Build Failed

**Error:** `Could not find requirements-web.txt`

**Fix:** Check "Root Directory" is set to:
```
projects/Life Automations/relationship-tracker
```

### Issue: Application Error on Visit

**Check the logs:**
1. Go to Render dashboard
2. Click your service
3. Click "Logs" tab
4. Look for Python errors

**Common fixes:**
- Add missing environment variables
- Check Google credentials are valid
- Verify all imports work

### Issue: Restaurants Not Loading

**Check:**
1. API endpoint works: `/api/restaurants`
2. Google Calendar credentials are set
3. Logs show no authentication errors

**Temporary fix:**
The app will still work - it just won't show visit history until credentials are configured.

### Issue: App Sleeps After Inactivity

**Expected behavior on free tier:**
- App sleeps after 15 minutes of inactivity
- Takes ~30 seconds to wake up on first visit
- This is normal for Render free tier

**Workaround:**
Use a service like UptimeRobot to ping your app every 10 minutes (keeps it awake).

---

## Alternative: Manual Deploy (If GitHub Not Available)

### Option 1: Deploy via CLI

```bash
# Install Render CLI
brew install render

# Login
render login

# Deploy
cd ~/personal-workspace-1/projects/Life\ Automations/relationship-tracker
render deploy
```

### Option 2: Deploy Manually

1. Create a `.zip` of the relationship-tracker folder
2. Upload to Render via "Deploy from ZIP"
3. Follow same configuration steps

---

## Post-Deployment Checklist

After successful deployment:

- [ ] Service is live at your Render URL
- [ ] Can visit the restaurant page in browser
- [ ] API endpoint returns restaurant data
- [ ] config.yaml updated with new URL
- [ ] New email sent with updated button
- [ ] Button in email links to Render URL
- [ ] Restaurant page loads correctly from email

---

## Monitoring & Maintenance

### View Logs

1. Go to Render dashboard
2. Click your service
3. Click "Logs" to see real-time output

### Update the App

Just push to GitHub:
```bash
git add .
git commit -m "Update restaurants or features"
git push origin main
```

Render will auto-deploy!

### Check Usage

Free tier includes:
- ✅ 750 hours/month (more than enough)
- ✅ Automatic HTTPS
- ✅ Unlimited bandwidth
- ⚠️ App sleeps after 15min inactivity

---

## Success!

Your restaurant discovery app is now deployed to the cloud! 🎉

**Your URL:** https://atlanta-date-restaurants.onrender.com

**Features:**
- ✅ Accessible from anywhere
- ✅ Mobile-friendly
- ✅ HTTPS secure
- ✅ Free forever
- ✅ Auto-deploys on git push
- ✅ Integrated with email reports

**Next time you send an email report, the button will link to your live Render app!**

---

## Quick Reference

**Render Dashboard:** https://dashboard.render.com
**Your Service:** https://dashboard.render.com/web/[your-service-id]
**Live App:** https://atlanta-date-restaurants.onrender.com
**Logs:** Dashboard → Your Service → Logs
**Settings:** Dashboard → Your Service → Settings
