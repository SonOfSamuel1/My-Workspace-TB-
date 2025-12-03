#!/usr/bin/env python3
"""
AWS CloudWatch Integration for My Workspace Security
Provides monitoring, alerting, and log aggregation for Lambda functions
"""

import os
import json
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CloudWatchSecurityIntegration:
    """
    Integrates security monitoring with AWS CloudWatch
    """

    def __init__(self, region: str = None):
        """Initialize CloudWatch clients"""
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')

        try:
            self.logs_client = boto3.client('logs', region_name=self.region)
            self.cloudwatch_client = boto3.client('cloudwatch', region_name=self.region)
            self.lambda_client = boto3.client('lambda', region_name=self.region)
            logger.info(f"CloudWatch integration initialized for region: {self.region}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise

    def setup_log_groups(self, apps: List[str]) -> Dict[str, bool]:
        """
        Create CloudWatch log groups for applications

        Args:
            apps: List of application names

        Returns:
            Dictionary of app names and creation status
        """
        results = {}

        for app in apps:
            log_group = f"/aws/lambda/{app}"

            try:
                # Create log group
                self.logs_client.create_log_group(
                    logGroupName=log_group,
                    tags={
                        'Application': app,
                        'Environment': 'production',
                        'SecurityMonitoring': 'enabled'
                    }
                )

                # Set retention policy (30 days)
                self.logs_client.put_retention_policy(
                    logGroupName=log_group,
                    retentionInDays=30
                )

                # Create metric filter for errors
                self.logs_client.put_metric_filter(
                    logGroupName=log_group,
                    filterName=f"{app}-errors",
                    filterPattern='[time, request_id, level = "ERROR", ...]',
                    metricTransformations=[
                        {
                            'metricName': 'ErrorCount',
                            'metricNamespace': f'MyWorkspace/{app}',
                            'metricValue': '1',
                            'unit': 'Count'
                        }
                    ]
                )

                # Create metric filter for security events
                self.logs_client.put_metric_filter(
                    logGroupName=log_group,
                    filterName=f"{app}-security",
                    filterPattern='SECURITY_VIOLATION OR AUTH_FAILURE OR RATE_LIMIT',
                    metricTransformations=[
                        {
                            'metricName': 'SecurityEvents',
                            'metricNamespace': f'MyWorkspace/{app}',
                            'metricValue': '1',
                            'unit': 'Count'
                        }
                    ]
                )

                results[app] = True
                logger.info(f"Created log group and filters for {app}")

            except self.logs_client.exceptions.ResourceAlreadyExistsException:
                results[app] = True
                logger.info(f"Log group already exists for {app}")
            except Exception as e:
                results[app] = False
                logger.error(f"Failed to create log group for {app}: {e}")

        return results

    def create_alarms(self, app: str) -> List[str]:
        """
        Create CloudWatch alarms for security monitoring

        Args:
            app: Application name

        Returns:
            List of created alarm names
        """
        alarms = []

        # Error rate alarm
        try:
            alarm_name = f"{app}-high-error-rate"
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=2,
                MetricName='ErrorCount',
                Namespace=f'MyWorkspace/{app}',
                Period=300,  # 5 minutes
                Statistic='Sum',
                Threshold=10,
                ActionsEnabled=True,
                AlarmDescription=f'Alarm when {app} error count exceeds 10 in 5 minutes',
                TreatMissingData='notBreaching'
            )
            alarms.append(alarm_name)
            logger.info(f"Created error rate alarm: {alarm_name}")
        except Exception as e:
            logger.error(f"Failed to create error rate alarm: {e}")

        # Security event alarm
        try:
            alarm_name = f"{app}-security-events"
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=1,
                MetricName='SecurityEvents',
                Namespace=f'MyWorkspace/{app}',
                Period=300,
                Statistic='Sum',
                Threshold=5,
                ActionsEnabled=True,
                AlarmDescription=f'Alarm when {app} has security events',
                TreatMissingData='notBreaching'
            )
            alarms.append(alarm_name)
            logger.info(f"Created security event alarm: {alarm_name}")
        except Exception as e:
            logger.error(f"Failed to create security event alarm: {e}")

        # Lambda throttling alarm
        try:
            alarm_name = f"{app}-lambda-throttles"
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=1,
                MetricName='Throttles',
                Namespace='AWS/Lambda',
                Dimensions=[{'Name': 'FunctionName', 'Value': app}],
                Period=300,
                Statistic='Sum',
                Threshold=5,
                ActionsEnabled=True,
                AlarmDescription=f'Alarm when {app} Lambda is throttled',
                TreatMissingData='notBreaching'
            )
            alarms.append(alarm_name)
            logger.info(f"Created throttling alarm: {alarm_name}")
        except Exception as e:
            logger.error(f"Failed to create throttling alarm: {e}")

        # Lambda duration alarm
        try:
            alarm_name = f"{app}-lambda-duration"
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=2,
                MetricName='Duration',
                Namespace='AWS/Lambda',
                Dimensions=[{'Name': 'FunctionName', 'Value': app}],
                Period=300,
                Statistic='Average',
                Threshold=30000,  # 30 seconds
                ActionsEnabled=True,
                AlarmDescription=f'Alarm when {app} Lambda duration exceeds 30 seconds',
                TreatMissingData='notBreaching'
            )
            alarms.append(alarm_name)
            logger.info(f"Created duration alarm: {alarm_name}")
        except Exception as e:
            logger.error(f"Failed to create duration alarm: {e}")

        return alarms

    def create_dashboard(self, apps: List[str]) -> str:
        """
        Create CloudWatch dashboard for security monitoring

        Args:
            apps: List of application names

        Returns:
            Dashboard name
        """
        dashboard_name = "MyWorkspace-Security"

        # Build widget list
        widgets = []
        row = 0

        for app in apps:
            # Error count widget
            widgets.append({
                "type": "metric",
                "x": 0,
                "y": row,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        [f"MyWorkspace/{app}", "ErrorCount", {"stat": "Sum"}],
                        [".", "SecurityEvents", {"stat": "Sum"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": self.region,
                    "title": f"{app} - Errors and Security Events",
                    "period": 300
                }
            })

            # Lambda metrics widget
            widgets.append({
                "type": "metric",
                "x": 12,
                "y": row,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["AWS/Lambda", "Duration", {"name": "FunctionName", "value": app}],
                        [".", "Errors", {"name": "FunctionName", "value": app}],
                        [".", "Throttles", {"name": "FunctionName", "value": app}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": self.region,
                    "title": f"{app} - Lambda Metrics",
                    "period": 300
                }
            })

            row += 6

        # Add summary widget
        widgets.insert(0, {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 24,
            "height": 3,
            "properties": {
                "metrics": [
                    ["MyWorkspace/autonomous-email-assistant", "SecurityEvents", {"stat": "Sum", "label": "Email Assistant"}],
                    ["MyWorkspace/weekly-budget-report", "SecurityEvents", {"stat": "Sum", "label": "Budget Report"}]
                ],
                "view": "singleValue",
                "region": self.region,
                "title": "Security Events Summary (Last 24 Hours)",
                "period": 86400
            }
        })

        # Create dashboard
        dashboard_body = {
            "widgets": widgets
        }

        try:
            self.cloudwatch_client.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            logger.info(f"Created dashboard: {dashboard_name}")
            return dashboard_name
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return ""

    def setup_log_insights_queries(self) -> Dict[str, str]:
        """
        Create saved CloudWatch Insights queries for security analysis

        Returns:
            Dictionary of query names and IDs
        """
        queries = {
            "security_violations": """
                fields @timestamp, @message
                | filter @message like /SECURITY_VIOLATION|CRITICAL/
                | sort @timestamp desc
                | limit 100
            """,
            "authentication_failures": """
                fields @timestamp, @message, user
                | filter @message like /AUTH_FAILURE/
                | stats count() by user
                | sort count desc
            """,
            "rate_limit_violations": """
                fields @timestamp, @message, app
                | filter @message like /RATE_LIMIT/
                | stats count() by bin(5m) as time_window
            """,
            "api_usage": """
                fields @timestamp, api, status_code
                | filter @message like /API_CALL/
                | stats count() by api, status_code
            """,
            "error_analysis": """
                fields @timestamp, @message, error_type
                | filter level = "ERROR"
                | stats count() by error_type
                | sort count desc
            """
        }

        # Note: CloudWatch Insights doesn't have an API to save queries programmatically
        # These would need to be saved manually in the console
        # Return the queries for documentation

        return queries

    def get_security_metrics(self, app: str, hours: int = 24) -> Dict:
        """
        Get security metrics for an application

        Args:
            app: Application name
            hours: Number of hours to look back

        Returns:
            Dictionary of metrics
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        metrics = {}

        # Get error count
        try:
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace=f'MyWorkspace/{app}',
                MetricName='ErrorCount',
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour
                Statistics=['Sum']
            )
            metrics['error_count'] = sum([d['Sum'] for d in response['Datapoints']])
        except Exception as e:
            logger.error(f"Failed to get error count: {e}")
            metrics['error_count'] = 0

        # Get security events
        try:
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace=f'MyWorkspace/{app}',
                MetricName='SecurityEvents',
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            metrics['security_events'] = sum([d['Sum'] for d in response['Datapoints']])
        except Exception as e:
            logger.error(f"Failed to get security events: {e}")
            metrics['security_events'] = 0

        # Get Lambda metrics
        try:
            # Invocations
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[{'Name': 'FunctionName', 'Value': app}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            metrics['invocations'] = sum([d['Sum'] for d in response['Datapoints']])

            # Errors
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Errors',
                Dimensions=[{'Name': 'FunctionName', 'Value': app}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            metrics['lambda_errors'] = sum([d['Sum'] for d in response['Datapoints']])

            # Average duration
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Duration',
                Dimensions=[{'Name': 'FunctionName', 'Value': app}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            durations = [d['Average'] for d in response['Datapoints']]
            metrics['avg_duration_ms'] = sum(durations) / len(durations) if durations else 0

        except Exception as e:
            logger.error(f"Failed to get Lambda metrics: {e}")

        return metrics

    def search_logs(self, app: str, query: str, hours: int = 1) -> List[Dict]:
        """
        Search CloudWatch logs using Insights

        Args:
            app: Application name
            query: CloudWatch Insights query
            hours: Number of hours to search

        Returns:
            List of log entries
        """
        log_group = f"/aws/lambda/{app}"
        end_time = int(datetime.utcnow().timestamp())
        start_time = end_time - (hours * 3600)

        try:
            # Start query
            response = self.logs_client.start_query(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                queryString=query
            )

            query_id = response['queryId']

            # Wait for query to complete
            status = 'Running'
            while status == 'Running':
                response = self.logs_client.get_query_results(queryId=query_id)
                status = response['status']

            if status == 'Complete':
                return response['results']
            else:
                logger.error(f"Query failed with status: {status}")
                return []

        except Exception as e:
            logger.error(f"Failed to search logs: {e}")
            return []


def setup_cloudwatch_for_app(app_name: str):
    """Setup CloudWatch monitoring for a specific application"""
    integration = CloudWatchSecurityIntegration()

    print(f"Setting up CloudWatch for {app_name}...")

    # Create log groups
    print("Creating log groups...")
    integration.setup_log_groups([app_name])

    # Create alarms
    print("Creating alarms...")
    alarms = integration.create_alarms(app_name)
    print(f"Created {len(alarms)} alarms")

    # Create dashboard
    print("Creating dashboard...")
    dashboard = integration.create_dashboard([app_name])
    print(f"Dashboard: {dashboard}")

    # Get current metrics
    print("\nCurrent metrics (last 24 hours):")
    metrics = integration.get_security_metrics(app_name)
    for key, value in metrics.items():
        print(f"  {key}: {value}")


def main():
    """CLI interface for CloudWatch integration"""
    import argparse

    parser = argparse.ArgumentParser(description="CloudWatch Security Integration")
    parser.add_argument("action",
                       choices=["setup", "metrics", "search", "test"],
                       help="Action to perform")
    parser.add_argument("--app", help="Application name")
    parser.add_argument("--query", help="CloudWatch Insights query")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back")

    args = parser.parse_args()

    integration = CloudWatchSecurityIntegration()

    if args.action == "setup":
        if not args.app:
            # Setup for all apps
            apps = ["autonomous-email-assistant", "weekly-budget-report"]
        else:
            apps = [args.app]

        print(f"Setting up CloudWatch for: {', '.join(apps)}")

        # Create log groups
        results = integration.setup_log_groups(apps)
        for app, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {app}: {status}")

        # Create alarms
        for app in apps:
            alarms = integration.create_alarms(app)
            print(f"  {app}: {len(alarms)} alarms created")

        # Create dashboard
        dashboard = integration.create_dashboard(apps)
        print(f"\nDashboard created: {dashboard}")

    elif args.action == "metrics":
        if not args.app:
            print("Error: --app required for metrics")
            return

        metrics = integration.get_security_metrics(args.app, args.hours)
        print(f"Metrics for {args.app} (last {args.hours} hours):")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

    elif args.action == "search":
        if not args.app or not args.query:
            print("Error: --app and --query required for search")
            return

        results = integration.search_logs(args.app, args.query, args.hours)
        print(f"Search results ({len(results)} entries):")
        for result in results[:10]:  # Show first 10
            print(json.dumps(result, indent=2))

    elif args.action == "test":
        print("Testing CloudWatch connection...")
        try:
            integration.logs_client.describe_log_groups(limit=1)
            print("✓ CloudWatch Logs connected")
        except:
            print("✗ CloudWatch Logs connection failed")

        try:
            integration.cloudwatch_client.list_metrics(limit=1)
            print("✓ CloudWatch Metrics connected")
        except:
            print("✗ CloudWatch Metrics connection failed")


if __name__ == "__main__":
    main()