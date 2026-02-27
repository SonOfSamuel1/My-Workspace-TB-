"""
NetWorthReportGenerator - Generates HTML email reports for weekly net worth & run rate.
"""

from datetime import datetime


class NetWorthReportGenerator:
    def __init__(self, config: dict):
        self.config = config

    def _format_currency(self, amount: float) -> str:
        """Format a float as $XX,XXX.XX with commas."""
        return f"${amount:,.2f}"

    def _color_for_value(self, amount: float) -> str:
        """Return green for positive, red for negative."""
        return "#53d769" if amount >= 0 else "#e94560"

    def _format_month(self, month_str: str) -> str:
        """Convert YYYY-MM to a readable month label like 'Jan 2026'."""
        try:
            dt = datetime.strptime(month_str, "%Y-%m")
            return dt.strftime("%b %Y")
        except ValueError:
            return month_str

    def _format_generated_at(self, generated_at: str) -> str:
        """Format ISO timestamp to a readable date string."""
        try:
            dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            return dt.strftime("%B %d, %Y")
        except (ValueError, AttributeError):
            return generated_at

    def _build_account_rows(
        self, accounts: list, section_label: str, label_color: str
    ) -> str:
        """Build HTML rows for a list of accounts sorted by balance descending."""
        if not accounts:
            return ""

        sorted_accounts = sorted(
            accounts, key=lambda a: a.get("balance", 0), reverse=True
        )

        rows_html = f"""
        <tr>
          <td colspan="3" style="padding: 12px 16px 6px 16px; font-size: 11px; font-weight: 700;
              letter-spacing: 1.5px; text-transform: uppercase; color: {label_color};">
            {section_label}
          </td>
        </tr>"""

        for account in sorted_accounts:
            name = account.get("name", "Unknown")
            balance = account.get("balance", 0.0)
            acct_type = account.get("type", "").replace("_", " ").title()
            balance_color = self._color_for_value(balance)

            rows_html += f"""
        <tr>
          <td style="padding: 9px 16px; font-size: 13px; color: #c9d1d9; border-bottom: 1px solid #0f3460;">
            {name}
          </td>
          <td style="padding: 9px 16px; font-size: 12px; color: #8b949e; border-bottom: 1px solid #0f3460;
              text-align: center;">
            {acct_type}
          </td>
          <td style="padding: 9px 16px; font-size: 13px; font-weight: 600; color: {balance_color};
              border-bottom: 1px solid #0f3460; text-align: right;">
            {self._format_currency(balance)}
          </td>
        </tr>"""

        return rows_html

    def generate_html_report(self, report_data: dict) -> str:
        """Generate and return a complete HTML email string."""

        net_worth = report_data.get("net_worth", 0.0)
        total_assets = report_data.get("total_assets", 0.0)
        total_liabilities = report_data.get("total_liabilities", 0.0)
        asset_accounts = report_data.get("asset_accounts", [])
        liability_accounts = report_data.get("liability_accounts", [])

        avg_income = report_data.get("avg_monthly_income", 0.0)
        avg_expenses = report_data.get("avg_monthly_expenses", 0.0)
        avg_net = report_data.get("avg_monthly_net", 0.0)
        annual_run_rate = report_data.get("annual_run_rate", 0.0)

        monthly_breakdown = report_data.get("monthly_breakdown", [])
        months_analyzed = report_data.get("months_analyzed", 0)
        generated_at = report_data.get("generated_at", "")
        data_sources = report_data.get("data_sources", {})

        # Formatted values
        net_worth_color = self._color_for_value(net_worth)
        net_worth_str = self._format_currency(net_worth)
        assets_str = self._format_currency(total_assets)
        liabilities_str = self._format_currency(total_liabilities)

        avg_income_str = self._format_currency(avg_income)
        avg_expenses_str = self._format_currency(avg_expenses)
        avg_net_str = self._format_currency(avg_net)
        avg_net_color = self._color_for_value(avg_net)
        annual_run_rate_str = self._format_currency(annual_run_rate)
        annual_run_rate_color = self._color_for_value(annual_run_rate)

        report_date = self._format_generated_at(generated_at)

        # Account rows
        asset_rows = self._build_account_rows(asset_accounts, "Assets", "#53d769")
        liability_rows = self._build_account_rows(
            liability_accounts, "Liabilities", "#e94560"
        )

        # Monthly trend rows
        monthly_rows_html = ""
        for entry in monthly_breakdown:
            month_label = self._format_month(entry.get("month", ""))
            income = entry.get("income", 0.0)
            expenses = entry.get("expenses", 0.0)
            net = entry.get("net", 0.0)
            net_color = self._color_for_value(net)

            monthly_rows_html += f"""
            <tr>
              <td style="padding: 9px 12px; font-size: 13px; color: #c9d1d9;
                  border-bottom: 1px solid #0f3460; text-align: center;">
                {month_label}
              </td>
              <td style="padding: 9px 12px; font-size: 13px; color: #53d769;
                  border-bottom: 1px solid #0f3460; text-align: right;">
                {self._format_currency(income)}
              </td>
              <td style="padding: 9px 12px; font-size: 13px; color: #e94560;
                  border-bottom: 1px solid #0f3460; text-align: right;">
                {self._format_currency(expenses)}
              </td>
              <td style="padding: 9px 12px; font-size: 13px; font-weight: 600; color: {net_color};
                  border-bottom: 1px solid #0f3460; text-align: right;">
                {self._format_currency(net)}
              </td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Net Worth Report</title>
  <style>
    @media only screen and (max-width: 600px) {{
      .email-container {{ width: 100% !important; }}
      .hero-net-worth {{ font-size: 36px !important; }}
      .hero-sub {{ font-size: 13px !important; }}
      .section-card {{ padding: 16px !important; }}
      .run-rate-grid {{ display: block !important; }}
      .run-rate-cell {{ display: block !important; width: 100% !important;
          border-right: none !important; border-bottom: 1px solid #0f3460 !important;
          margin-bottom: 0 !important; }}
    }}
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #111120; font-family: -apple-system, BlinkMacSystemFont,
    'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
      style="background-color: #111120; padding: 32px 0;">
    <tr>
      <td align="center">

        <!-- Email Container -->
        <table class="email-container" width="600" cellpadding="0" cellspacing="0" border="0"
            style="max-width: 600px; width: 100%; background-color: #1a1a2e;
            border-radius: 12px; overflow: hidden; border: 1px solid #0f3460;">

          <!-- ===== HEADER ===== -->
          <tr>
            <td style="background: linear-gradient(135deg, #0f3460 0%, #1a1a2e 100%);
                padding: 28px 32px 24px 32px; border-bottom: 2px solid #e94560;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td>
                    <div style="font-size: 11px; letter-spacing: 2.5px; text-transform: uppercase;
                        color: #e94560; font-weight: 700; margin-bottom: 4px;">
                      Weekly Report
                    </div>
                    <div style="font-size: 24px; font-weight: 700; color: #ffffff; line-height: 1.2;">
                      Net Worth Report
                    </div>
                  </td>
                  <td align="right" style="vertical-align: bottom;">
                    <div style="font-size: 12px; color: #8b949e; white-space: nowrap;">
                      {report_date}
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ===== NET WORTH HERO ===== -->
          <tr>
            <td style="padding: 32px 32px 24px 32px; background-color: #16213e;
                border-bottom: 1px solid #0f3460; text-align: center;">
              <div style="font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
                  color: #8b949e; margin-bottom: 12px; font-weight: 600;">
                Total Net Worth
              </div>
              <div class="hero-net-worth"
                  style="font-size: 52px; font-weight: 800; color: {net_worth_color};
                  letter-spacing: -1px; line-height: 1.1; margin-bottom: 20px;">
                {net_worth_str}
              </div>
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" width="50%"
                      style="border-right: 1px solid #0f3460; padding: 12px 0;">
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px;
                        color: #8b949e; margin-bottom: 4px; font-weight: 600;">
                      Total Assets
                    </div>
                    <div class="hero-sub"
                        style="font-size: 18px; font-weight: 700; color: #53d769;">
                      {assets_str}
                    </div>
                  </td>
                  <td align="center" width="50%" style="padding: 12px 0;">
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px;
                        color: #8b949e; margin-bottom: 4px; font-weight: 600;">
                      Total Liabilities
                    </div>
                    <div class="hero-sub"
                        style="font-size: 18px; font-weight: 700; color: #e94560;">
                      {liabilities_str}
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ===== RUN RATE SUMMARY ===== -->
          <tr>
            <td class="section-card" style="padding: 24px 32px; border-bottom: 1px solid #0f3460;">
              <div style="font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
                  color: #8b949e; margin-bottom: 16px; font-weight: 600;">
                Run Rate Summary
                <span style="color: #4a5568; font-size: 10px; letter-spacing: 1px;">
                  ({months_analyzed}-month avg)
                </span>
              </div>

              <!-- Annual Run Rate Prominent -->
              <div style="background-color: #0f3460; border-radius: 8px; padding: 16px 20px;
                  margin-bottom: 16px; text-align: center; border: 1px solid #1a4a80;">
                <div style="font-size: 10px; letter-spacing: 2px; text-transform: uppercase;
                    color: #8b949e; margin-bottom: 6px; font-weight: 700;">
                  Annual Run Rate
                </div>
                <div style="font-size: 32px; font-weight: 800; color: {annual_run_rate_color};
                    letter-spacing: -0.5px;">
                  {annual_run_rate_str}
                </div>
              </div>

              <!-- Monthly breakdown grid -->
              <table class="run-rate-grid" width="100%" cellpadding="0" cellspacing="0" border="0"
                  style="border: 1px solid #0f3460; border-radius: 8px; overflow: hidden;">
                <tr>
                  <td class="run-rate-cell" width="33.33%"
                      style="padding: 14px 16px; text-align: center;
                      border-right: 1px solid #0f3460; background-color: #1a2a1a;">
                    <div style="font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase;
                        color: #8b949e; margin-bottom: 6px; font-weight: 600;">
                      Avg Income
                    </div>
                    <div style="font-size: 17px; font-weight: 700; color: #53d769;">
                      {avg_income_str}
                    </div>
                  </td>
                  <td class="run-rate-cell" width="33.33%"
                      style="padding: 14px 16px; text-align: center;
                      border-right: 1px solid #0f3460; background-color: #1a1020;">
                    <div style="font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase;
                        color: #8b949e; margin-bottom: 6px; font-weight: 600;">
                      Avg Expenses
                    </div>
                    <div style="font-size: 17px; font-weight: 700; color: #e94560;">
                      {avg_expenses_str}
                    </div>
                  </td>
                  <td class="run-rate-cell" width="33.33%"
                      style="padding: 14px 16px; text-align: center;
                      background-color: #161626;">
                    <div style="font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase;
                        color: #8b949e; margin-bottom: 6px; font-weight: 600;">
                      Avg Net
                    </div>
                    <div style="font-size: 17px; font-weight: 700; color: {avg_net_color};">
                      {avg_net_str}
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ===== ACCOUNT BALANCES ===== -->
          <tr>
            <td class="section-card" style="padding: 24px 32px; border-bottom: 1px solid #0f3460;">
              <div style="font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
                  color: #8b949e; margin-bottom: 16px; font-weight: 600;">
                Account Balances
              </div>

              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                  style="border: 1px solid #0f3460; border-radius: 8px; overflow: hidden;">
                <!-- Column Headers -->
                <tr style="background-color: #0f3460;">
                  <th style="padding: 10px 16px; font-size: 10px; letter-spacing: 1.5px;
                      text-transform: uppercase; color: #8b949e; text-align: left;
                      font-weight: 700; border-bottom: 1px solid #1a4a80;">
                    Account
                  </th>
                  <th style="padding: 10px 16px; font-size: 10px; letter-spacing: 1.5px;
                      text-transform: uppercase; color: #8b949e; text-align: center;
                      font-weight: 700; border-bottom: 1px solid #1a4a80;">
                    Type
                  </th>
                  <th style="padding: 10px 16px; font-size: 10px; letter-spacing: 1.5px;
                      text-transform: uppercase; color: #8b949e; text-align: right;
                      font-weight: 700; border-bottom: 1px solid #1a4a80;">
                    Balance
                  </th>
                </tr>
                {asset_rows}
                {liability_rows}
              </table>
            </td>
          </tr>

          <!-- ===== MONTHLY TREND ===== -->
          <tr>
            <td class="section-card" style="padding: 24px 32px; border-bottom: 1px solid #0f3460;">
              <div style="font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
                  color: #8b949e; margin-bottom: 16px; font-weight: 600;">
                Monthly Trend
              </div>

              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                  style="border: 1px solid #0f3460; border-radius: 8px; overflow: hidden;">
                <tr style="background-color: #0f3460;">
                  <th style="padding: 10px 12px; font-size: 10px; letter-spacing: 1.5px;
                      text-transform: uppercase; color: #8b949e; text-align: center;
                      font-weight: 700; border-bottom: 1px solid #1a4a80;">
                    Month
                  </th>
                  <th style="padding: 10px 12px; font-size: 10px; letter-spacing: 1.5px;
                      text-transform: uppercase; color: #8b949e; text-align: right;
                      font-weight: 700; border-bottom: 1px solid #1a4a80;">
                    Income
                  </th>
                  <th style="padding: 10px 12px; font-size: 10px; letter-spacing: 1.5px;
                      text-transform: uppercase; color: #8b949e; text-align: right;
                      font-weight: 700; border-bottom: 1px solid #1a4a80;">
                    Expenses
                  </th>
                  <th style="padding: 10px 12px; font-size: 10px; letter-spacing: 1.5px;
                      text-transform: uppercase; color: #8b949e; text-align: right;
                      font-weight: 700; border-bottom: 1px solid #1a4a80;">
                    Net
                  </th>
                </tr>
                {monthly_rows_html if monthly_rows_html else
                  '<tr><td colspan="4" style="padding: 16px; text-align: center; color: #8b949e; font-size: 13px;">No monthly data available.</td></tr>'}  # noqa: E501
              </table>
            </td>
          </tr>

          <!-- ===== FOOTER ===== -->
          <tr>
            <td style="padding: 20px 32px; background-color: #0f1a2e; text-align: center;
                border-top: 1px solid #0f3460;">
              <div style="font-size: 11px; color: #4a5568; letter-spacing: 0.5px;">
                Generated by
                <span style="color: #8b949e; font-weight: 600;">Net Worth Report</span>
                {(' | Net Worth: ' + data_sources.get('net_worth', '') + ' | Run Rate: ' + data_sources.get('run_rate', '')) if data_sources else ''}  # noqa: E501
              </div>
              <div style="font-size: 10px; color: #4a5568; margin-top: 4px;">
                {generated_at}
              </div>
            </td>
          </tr>

        </table>
        <!-- /Email Container -->

      </td>
    </tr>
  </table>
  <!-- /Wrapper -->

</body>
</html>"""

        return html
