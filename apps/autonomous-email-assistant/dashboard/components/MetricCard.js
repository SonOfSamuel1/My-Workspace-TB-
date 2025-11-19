/**
 * Metric Card Component
 * Displays a single metric with icon and optional trend
 */

export default function MetricCard({ title, value, icon: Icon, color, trend, subtitle, urgent }) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    indigo: 'bg-indigo-50 text-indigo-600',
    teal: 'bg-teal-50 text-teal-600'
  };

  const iconClass = colorClasses[color] || colorClasses.blue;

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${urgent ? 'ring-2 ring-red-500' : ''}`}>
      <div className="flex items-center">
        <div className={`flex-shrink-0 rounded-md p-3 ${iconClass}`}>
          <Icon className="h-6 w-6" aria-hidden="true" />
        </div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">
              {title}
            </dt>
            <dd className="flex items-baseline">
              <div className="text-2xl font-semibold text-gray-900">
                {value}
              </div>
              {trend && (
                <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                  trend.startsWith('+') ? 'text-green-600' : 'text-red-600'
                }`}>
                  {trend}
                </div>
              )}
            </dd>
            {subtitle && (
              <dd className="text-sm text-gray-500 mt-1">
                {subtitle}
              </dd>
            )}
          </dl>
        </div>
      </div>
    </div>
  );
}
