# Email Assistant Dashboard

Modern web dashboard for monitoring and managing the Autonomous Email Assistant.

## Features

- **Real-time Metrics**: Live dashboard with email processing statistics
- **Email Management**: View and manage recent emails
- **Approval Queue**: Review and approve draft responses
- **Analytics**: Comprehensive charts and insights
- **Responsive Design**: Works on desktop and mobile

## Tech Stack

- **Framework**: Next.js 14
- **UI**: React 18 + TailwindCSS
- **Charts**: Recharts
- **Icons**: Heroicons
- **Data Fetching**: SWR (React Hooks for Data Fetching)

## Getting Started

### Installation

```bash
cd dashboard
npm install
```

### Development

```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### Production Build

```bash
npm run build
npm start
```

## API Endpoints

The dashboard connects to the following API endpoints:

- `GET /api/metrics` - Comprehensive metrics and analytics
- `GET /api/emails/recent` - Recent email list
- `GET /api/approvals/pending` - Pending draft approvals

## Environment Variables

Create `.env.local`:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:3000/api

# Optional: Analytics
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
```

## Deployment

### Vercel (Recommended)

```bash
npm install -g vercel
vercel deploy
```

### Docker

```bash
docker build -t email-dashboard .
docker run -p 3000:3000 email-dashboard
```

### AWS Amplify

1. Connect your GitHub repository
2. Set build settings:
   - Build command: `npm run build`
   - Output directory: `.next`
3. Deploy

## Project Structure

```
dashboard/
├── pages/              # Next.js pages
│   ├── index.js       # Dashboard home
│   ├── _app.js        # App configuration
│   └── api/           # API routes
├── components/         # React components
│   ├── MetricCard.js
│   ├── EmailList.js
│   ├── VolumeChart.js
│   ├── TierDistribution.js
│   └── PendingApprovals.js
├── styles/            # CSS styles
│   └── globals.css
├── lib/               # Utility functions
├── public/            # Static assets
└── package.json
```

## Key Components

### MetricCard

Displays a single metric with icon and optional trend indicator.

```jsx
<MetricCard
  title="Emails Today"
  value={47}
  icon={EnvelopeIcon}
  color="blue"
  trend="+12.5%"
/>
```

### EmailList

Displays list of recent emails with status badges.

### VolumeChart

Line chart showing email volume over time.

### TierDistribution

Bar chart showing email tier distribution.

### PendingApprovals

Interactive component for reviewing and approving draft responses.

## Customization

### Theme Colors

Edit `tailwind.config.js`:

```js
theme: {
  extend: {
    colors: {
      primary: {
        // Your custom colors
      }
    }
  }
}
```

### Metrics

Add custom metrics in `pages/api/metrics.js`

### Charts

Customize charts in component files using Recharts configuration.

## Performance

- **SWR Caching**: Automatic request deduplication and caching
- **Auto Refresh**: Configurable refresh intervals for real-time data
- **Optimized Images**: Next.js automatic image optimization
- **Code Splitting**: Automatic code splitting for faster loads

## Security

- API authentication required in production
- CORS configuration
- Rate limiting recommended
- Secure environment variables

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT
