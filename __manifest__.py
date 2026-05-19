{
    'name': 'Advanced Marketing Reports',
    'version': '18.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Comprehensive reporting and intelligence for Email Marketing and Marketing Automation',
    'description': """
Advanced Marketing Reports
==========================
Provides 15 read-only SQL-backed report views covering:

- Email Marketing: Campaign Stats, Delivery Details
- Marketing Automation: Campaign Overview, Activity Stats, Participant Breakdown
- Insights: Monthly Trend, Campaign Ranking, Bounce & Failure Breakdown,
            Send Time Analysis, Subject Line Patterns, A/B Test Results,
            Trigger Effectiveness
- Intelligence: Contact Engagement Scoring, Mailing List Health, Re-engagement Opportunities

All models are _auto = False (SQL views only). All fields are readonly.
Zero write risk. Safe reinstall via drop_view_if_exists.
    """,
    'author': 'Custom',
    'depends': [
        'mass_mailing',
        'marketing_automation',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mailing_report_views.xml',
        'views/automation_report_views.xml',
        'views/insights_report_views.xml',
        'data/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
