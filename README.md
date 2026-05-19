# adv-marketing-reports

> 15 read-only SQL analytics views for email marketing and automation.  
> Campaign rankings. Engagement scoring. List health. Send-time analysis. A/B test results.

Part of the [enterprise-ai-agent](../enterprise-ai-agent) project — built by giving an AI agent plain English instructions and letting the WAT framework handle the rest.

---

## What it does

Extends the built-in email marketing and automation modules with 15 purpose-built reporting views — all read-only, all SQL-backed, zero write risk.

### Email marketing reports

| Report | What it shows |
|--------|--------------|
| **Campaign Stats** | Every sent campaign with open rate, click rate, bounce rate, delivery rate, reply rate |
| **Delivery Details** | Per-recipient trace — status, failure reason, timestamps for sent/opened/clicked/replied |

### Marketing automation reports

| Report | What it shows |
|--------|--------------|
| **Campaign Overview** | Participant counts, activity counts, email performance per automation campaign |
| **Activity Stats** | Per-activity breakdown — sent, opened, clicked, bounced, replied, processed, rejected |
| **Participant Breakdown** | Daily participant state breakdown — running, completed, removed, test |

### Insights reports

| Report | What it shows |
|--------|--------------|
| **Monthly Trend** | Month-over-month campaign volume and performance rates |
| **Campaign Ranking** | All campaigns ranked by engagement score (weighted: opens 40%, delivery 30%, replies 20%, minus bounces 10%) |
| **Bounce & Failure Breakdown** | Failure types with counts, % of total, affected campaigns, by month |
| **Send Time Analysis** | Open and click rates by hour of day and day of week — identifies best send windows |
| **Subject Line Patterns** | All subject lines with engagement metrics — compare length and wording impact |
| **A/B Test Results** | All A/B tested campaigns with variant performance and winner identification |
| **Trigger Effectiveness** | Automation trigger types ranked by average open and click rates |

### Intelligence reports

| Report | What it shows |
|--------|--------------|
| **Contact Engagement Scoring** | Per-email address engagement score — Highly Engaged / Moderate / Cold tiers |
| **Mailing List Health** | Per-list active %, bounce exposure, health score — Healthy / Average / Needs Cleaning |
| **Re-engagement Opportunities** | Contacts who haven't opened in 30/60/90+ days — Lost / Dormant / At Risk status |

---

## Design principles

**Read-only by design.** Every model uses `_auto = False` (PostgreSQL view, not a table). Every field is `readonly=True`. There is no way for this module to modify or delete your data.

**Safe to reinstall.** Every `init()` method calls `drop_view_if_exists` before creating the view. Reinstalling or upgrading is always safe.

**No external dependencies.** Pure SQL views on top of existing tables. No new database tables. No migrations.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Models | Python (`odoo.models.Model` with `_auto = False`) |
| Data layer | PostgreSQL SQL views — CTEs, window functions, aggregations |
| Views | XML list/graph/pivot views with filters and group-by |
| Access | CSV security rules — read-only for all users |

---

## Compatibility

- **Platform version**: 18.0
- **Depends on**: `mass_mailing`, `marketing_automation`
- **No new tables** — views only

---

## Installation

1. Copy the `advanced_marketing_reports` folder into your addons directory
2. Update your addons list
3. Install **Advanced Marketing Reports** from the Apps menu
4. Find reports under Email Marketing → Reports and Marketing Automation → Reports

---

## File structure

```
advanced_marketing_reports/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── mailing_report.py       # Campaign Stats, Delivery Details
│   ├── automation_report.py    # Campaign Overview, Activity Stats, Participant Breakdown
│   └── insights_report.py      # Monthly Trend, Campaign Ranking, Bounce, Send Time,
│                               # Subject Lines, A/B Tests, Trigger Effectiveness,
│                               # Contact Engagement, List Health, Re-engagement
├── views/
│   ├── mailing_report_views.xml
│   ├── automation_report_views.xml
│   └── insights_report_views.xml
├── data/
│   └── menu.xml                # Menu structure
└── security/
    └── ir.model.access.csv     # Read-only access rules
```

---

## How it was built

This module was built using the [enterprise-ai-agent](../enterprise-ai-agent) framework. The instruction given was roughly:

> "Build a comprehensive reporting module for email marketing and automation. I want to see campaign performance, per-recipient delivery traces, monthly trends, bounce analysis, best send times, subject line comparisons, A/B test results, contact engagement scores, list health, and re-engagement opportunities. Everything read-only."

The agent read the `generate_report` workflow, designed the SQL view architecture, and built each model iteratively — discovering the correct column names by inspecting the live database schema and correcting queries until every view created and populated successfully.

---

## SQL highlights

A few of the more interesting queries:

**Campaign Ranking** uses a weighted engagement score: `opens × 0.4 + delivery × 0.3 + replies × 0.2 − bounces × 0.1`, then ranks all campaigns with `RANK() OVER`.

**Send Time Analysis** unions two subqueries — by hour of day and by day of week — then applies `PERCENT_RANK() OVER` to label Best / Average / Worst slots per slot type.

**Contact Engagement Scoring** aggregates per-email across all campaigns, calculates a 0–100 engagement score, and buckets into tiers using `CASE WHEN`.

**Re-engagement Opportunities** identifies contacts who haven't opened in 30+ days and counts how many campaigns they've silently received since their last open — the key signal for list hygiene.

---

## Screenshots

*(Add screenshots here after installation)*

---

## License

LGPL-3 — same as the platform it extends.
