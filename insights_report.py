from odoo import fields, models, tools


# ── 6. Monthly Trend ─────────────────────────────────────────────────────────
class AmrMonthlyTrendReport(models.Model):
    _name = 'amr.monthly.trend.report'
    _description = 'Monthly Trend Report'
    _auto = False
    _rec_name = 'month_label'
    _order = 'year desc, month desc'

    month_label = fields.Char(string='Month', readonly=True)
    year = fields.Integer(string='Year', readonly=True)
    month = fields.Integer(string='Month #', readonly=True)
    campaigns_sent = fields.Integer(string='Campaigns Sent', readonly=True)
    total_sent = fields.Integer(string='Total Sent', readonly=True)
    total_delivered = fields.Integer(string='Delivered', readonly=True)
    total_opened = fields.Integer(string='Opened', readonly=True)
    total_clicked = fields.Integer(string='Clicked', readonly=True)
    total_bounced = fields.Integer(string='Bounced', readonly=True)
    open_rate = fields.Float(string='Open %', readonly=True, digits=(16, 2))
    click_rate = fields.Float(string='Click %', readonly=True, digits=(16, 2))
    bounce_rate = fields.Float(string='Bounce %', readonly=True, digits=(16, 2))
    delivery_rate = fields.Float(string='Delivery %', readonly=True, digits=(16, 2))

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_monthly_trend_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_monthly_trend_report AS
            WITH click_per_mailing AS (
                SELECT mass_mailing_id, COUNT(*) AS cnt
                FROM mailing_trace
                WHERE trace_status = 'click'
                GROUP BY mass_mailing_id
            )
            SELECT
                ROW_NUMBER() OVER (
                    ORDER BY EXTRACT(YEAR FROM m.sent_date) DESC,
                             EXTRACT(MONTH FROM m.sent_date) DESC
                )                                                               AS id,
                TO_CHAR(m.sent_date, 'Month YYYY')                             AS month_label,
                EXTRACT(YEAR  FROM m.sent_date)::int                           AS year,
                EXTRACT(MONTH FROM m.sent_date)::int                           AS month,
                COUNT(m.id)                                                     AS campaigns_sent,
                COALESCE(SUM(m.sent),    0)                                     AS total_sent,
                COALESCE(SUM(
                    GREATEST(0, COALESCE(m.sent,0) - COALESCE(m.bounced,0))
                ), 0)                                                           AS total_delivered,
                COALESCE(SUM(m.opened),  0)                                     AS total_opened,
                COALESCE(SUM(COALESCE(cpm.cnt, 0)), 0)                          AS total_clicked,
                COALESCE(SUM(m.bounced), 0)                                     AS total_bounced,
                ROUND(AVG(COALESCE(m.opened_ratio,   0))::numeric, 2)           AS open_rate,
                ROUND(AVG(
                    COALESCE(cpm.cnt, 0)::numeric / NULLIF(m.sent, 0) * 100
                )::numeric, 2)                                                  AS click_rate,
                ROUND(AVG(COALESCE(m.bounced_ratio,  0))::numeric, 2)           AS bounce_rate,
                ROUND(AVG(COALESCE(m.received_ratio, 0))::numeric, 2)           AS delivery_rate
            FROM mailing_mailing m
            LEFT JOIN click_per_mailing cpm ON cpm.mass_mailing_id = m.id
            WHERE m.mailing_type = 'mail'
              AND m.state = 'done'
              AND m.sent_date IS NOT NULL
            GROUP BY
                EXTRACT(YEAR  FROM m.sent_date),
                EXTRACT(MONTH FROM m.sent_date),
                TO_CHAR(m.sent_date, 'Month YYYY')
        """)


# ── 7. Campaign Ranking ───────────────────────────────────────────────────────
class AmrCampaignRankingReport(models.Model):
    _name = 'amr.campaign.ranking.report'
    _description = 'Campaign Ranking Report'
    _auto = False
    _rec_name = 'subject'
    _order = 'rank asc'

    mailing_id = fields.Many2one('mailing.mailing', string='Mailing', readonly=True)
    subject = fields.Char(string='Subject', readonly=True)
    rank = fields.Integer(string='Rank', readonly=True)
    engagement_score = fields.Float(string='Engagement Score', readonly=True, digits=(16, 2))
    performance_tier = fields.Char(string='Performance Tier', readonly=True)
    open_rate = fields.Float(string='Open %', readonly=True, digits=(16, 2))
    click_rate = fields.Float(string='Click %', readonly=True, digits=(16, 2))
    delivery_rate = fields.Float(string='Delivery %', readonly=True, digits=(16, 2))
    reply_rate = fields.Float(string='Reply %', readonly=True, digits=(16, 2))
    bounce_rate = fields.Float(string='Bounce %', readonly=True, digits=(16, 2))
    sent_date = fields.Datetime(string='Sent Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_campaign_ranking_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_campaign_ranking_report AS
            WITH click_per_mailing AS (
                SELECT mass_mailing_id, COUNT(*) AS cnt
                FROM mailing_trace
                WHERE trace_status = 'click'
                GROUP BY mass_mailing_id
            ),
            scored AS (
                SELECT
                    m.id,
                    m.subject,
                    m.sent_date,
                    ROUND(COALESCE(m.opened_ratio,   0)::numeric, 2)            AS open_rate,
                    ROUND(
                        COALESCE(cpm.cnt,0)::numeric / NULLIF(m.sent,0) * 100
                    , 2)                                                         AS click_rate,
                    ROUND(COALESCE(m.received_ratio, 0)::numeric, 2)            AS delivery_rate,
                    ROUND(COALESCE(m.replied_ratio,  0)::numeric, 2)            AS reply_rate,
                    ROUND(COALESCE(m.bounced_ratio,  0)::numeric, 2)            AS bounce_rate,
                    ROUND((
                        COALESCE(m.opened_ratio,   0) * 0.4
                      + COALESCE(m.received_ratio, 0) * 0.3
                      + COALESCE(m.replied_ratio,  0) * 0.2
                      - COALESCE(m.bounced_ratio,  0) * 0.1
                    )::numeric, 2)                                               AS engagement_score
                FROM mailing_mailing m
                LEFT JOIN click_per_mailing cpm ON cpm.mass_mailing_id = m.id
                WHERE m.mailing_type = 'mail'
                  AND m.state = 'done'
            )
            SELECT
                id,
                id                                                               AS mailing_id,
                subject,
                sent_date,
                RANK() OVER (ORDER BY engagement_score DESC)::int               AS rank,
                engagement_score,
                CASE
                    WHEN engagement_score >= 40 THEN 'Top Performer'
                    WHEN engagement_score >= 20 THEN 'Average'
                    ELSE 'Needs Attention'
                END                                                              AS performance_tier,
                open_rate,
                click_rate,
                delivery_rate,
                reply_rate,
                bounce_rate
            FROM scored
        """)


# ── 8. Bounce & Failure Breakdown ─────────────────────────────────────────────
class AmrBounceReport(models.Model):
    _name = 'amr.bounce.report'
    _description = 'Bounce & Failure Breakdown'
    _auto = False
    _order = 'failure_count desc'

    failure_type = fields.Char(string='Failure Type', readonly=True)
    failure_count = fields.Integer(string='Count', readonly=True)
    pct_of_total = fields.Float(string='% of Total', readonly=True, digits=(16, 2))
    affected_campaigns = fields.Integer(string='Affected Campaigns', readonly=True)
    month_label = fields.Char(string='Month', readonly=True)
    year = fields.Integer(string='Year', readonly=True)
    month = fields.Integer(string='Month #', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_bounce_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_bounce_report AS
            WITH total_failures AS (
                SELECT COUNT(*) AS grand_total
                FROM mailing_trace
                WHERE failure_type IS NOT NULL
                  AND failure_type != ''
            ),
            grouped AS (
                SELECT
                    COALESCE(t.failure_type, 'unknown')         AS failure_type,
                    TO_CHAR(t.sent_datetime, 'Month YYYY')      AS month_label,
                    EXTRACT(YEAR  FROM t.sent_datetime)::int    AS year,
                    EXTRACT(MONTH FROM t.sent_datetime)::int    AS month,
                    COUNT(*)                                    AS failure_count,
                    COUNT(DISTINCT t.mass_mailing_id)           AS affected_campaigns
                FROM mailing_trace t
                INNER JOIN mailing_mailing m ON m.id = t.mass_mailing_id
                WHERE t.failure_type IS NOT NULL
                  AND t.failure_type != ''
                  AND m.mailing_type = 'mail'
                GROUP BY
                    t.failure_type,
                    TO_CHAR(t.sent_datetime, 'Month YYYY'),
                    EXTRACT(YEAR  FROM t.sent_datetime),
                    EXTRACT(MONTH FROM t.sent_datetime)
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY g.failure_count DESC) AS id,
                g.failure_type,
                g.month_label,
                g.year,
                g.month,
                g.failure_count,
                ROUND(
                    (g.failure_count::numeric / NULLIF(tf.grand_total, 0)) * 100, 2
                )                                                   AS pct_of_total,
                g.affected_campaigns
            FROM grouped g
            CROSS JOIN total_failures tf
        """)


# ── 9. Send Time Analysis ─────────────────────────────────────────────────────
class AmrSendtimeReport(models.Model):
    _name = 'amr.sendtime.report'
    _description = 'Send Time Analysis'
    _auto = False
    _order = 'avg_open_rate desc'

    slot_type = fields.Selection([
        ('hour', 'Hour of Day'),
        ('day', 'Day of Week'),
    ], string='Slot Type', readonly=True)
    slot_label = fields.Char(string='Hour / Day', readonly=True)
    slot_value = fields.Integer(string='Slot Value', readonly=True)
    campaigns_sent = fields.Integer(string='Campaigns Sent', readonly=True)
    avg_open_rate = fields.Float(string='Avg Open %', readonly=True, digits=(16, 2))
    avg_click_rate = fields.Float(string='Avg Click %', readonly=True, digits=(16, 2))
    performance_label = fields.Char(string='Performance', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_sendtime_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_sendtime_report AS
            WITH click_per_mailing AS (
                SELECT mass_mailing_id,
                       COUNT(*) AS cnt
                FROM mailing_trace
                WHERE trace_status = 'click'
                GROUP BY mass_mailing_id
            ),
            base AS (
                SELECT
                    m.id,
                    m.sent_date,
                    COALESCE(m.opened_ratio, 0)                                     AS open_rate,
                    COALESCE(cpm.cnt, 0)::numeric / NULLIF(m.sent, 0) * 100        AS click_rate
                FROM mailing_mailing m
                LEFT JOIN click_per_mailing cpm ON cpm.mass_mailing_id = m.id
                WHERE m.mailing_type = 'mail'
                  AND m.state = 'done'
                  AND m.sent_date IS NOT NULL
            ),
            by_hour AS (
                SELECT
                    'hour'                                                          AS slot_type,
                    LPAD(EXTRACT(HOUR FROM sent_date)::text, 2, '0') || ':00'      AS slot_label,
                    EXTRACT(HOUR FROM sent_date)::int                               AS slot_value,
                    COUNT(*)                                                        AS campaigns_sent,
                    ROUND(AVG(open_rate)::numeric, 2)                              AS avg_open_rate,
                    ROUND(AVG(COALESCE(click_rate, 0))::numeric, 2)                AS avg_click_rate
                FROM base
                GROUP BY EXTRACT(HOUR FROM sent_date)
            ),
            by_day AS (
                SELECT
                    'day'                                                           AS slot_type,
                    TRIM(TO_CHAR(sent_date, 'Day'))                                 AS slot_label,
                    EXTRACT(ISODOW FROM sent_date)::int                             AS slot_value,
                    COUNT(*)                                                        AS campaigns_sent,
                    ROUND(AVG(open_rate)::numeric, 2)                              AS avg_open_rate,
                    ROUND(AVG(COALESCE(click_rate, 0))::numeric, 2)                AS avg_click_rate
                FROM base
                GROUP BY TRIM(TO_CHAR(sent_date, 'Day')), EXTRACT(ISODOW FROM sent_date)
            ),
            combined AS (
                SELECT * FROM by_hour
                UNION ALL
                SELECT * FROM by_day
            ),
            ranked AS (
                SELECT *,
                    PERCENT_RANK() OVER (
                        PARTITION BY slot_type ORDER BY avg_open_rate
                    ) AS prank
                FROM combined
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY slot_type, slot_value) AS id,
                slot_type,
                slot_label,
                slot_value,
                campaigns_sent,
                avg_open_rate,
                avg_click_rate,
                CASE
                    WHEN prank >= 0.8 THEN 'Best'
                    WHEN prank <= 0.2 THEN 'Worst'
                    ELSE 'Average'
                END AS performance_label
            FROM ranked
        """)


# ── 10. Subject Line Pattern Analysis ─────────────────────────────────────────
class AmrSubjectReport(models.Model):
    _name = 'amr.subject.report'
    _description = 'Subject Line Pattern Analysis'
    _auto = False
    _rec_name = 'subject'
    _order = 'open_rate desc'

    mailing_id = fields.Many2one('mailing.mailing', string='Mailing', readonly=True)
    subject = fields.Char(string='Subject', readonly=True)
    subject_length = fields.Integer(string='Length (chars)', readonly=True)
    sent = fields.Integer(string='Sent', readonly=True)
    open_rate = fields.Float(string='Open %', readonly=True, digits=(16, 2))
    click_rate = fields.Float(string='Click %', readonly=True, digits=(16, 2))
    bounce_rate = fields.Float(string='Bounce %', readonly=True, digits=(16, 2))
    sent_date = fields.Datetime(string='Sent Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_subject_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_subject_report AS
            WITH click_per_mailing AS (
                SELECT mass_mailing_id, COUNT(*) AS cnt
                FROM mailing_trace
                WHERE trace_status = 'click'
                GROUP BY mass_mailing_id
            )
            SELECT
                m.id                                                            AS id,
                m.id                                                            AS mailing_id,
                m.subject                                                       AS subject,
                LENGTH(COALESCE(m.subject, ''))                                 AS subject_length,
                COALESCE(m.sent, 0)                                             AS sent,
                ROUND(COALESCE(m.opened_ratio,  0)::numeric, 2)                AS open_rate,
                ROUND(
                    COALESCE(cpm.cnt, 0)::numeric / NULLIF(m.sent, 0) * 100, 2
                )                                                               AS click_rate,
                ROUND(COALESCE(m.bounced_ratio, 0)::numeric, 2)                AS bounce_rate,
                m.sent_date                                                     AS sent_date
            FROM mailing_mailing m
            LEFT JOIN click_per_mailing cpm ON cpm.mass_mailing_id = m.id
            WHERE m.mailing_type = 'mail'
              AND m.state = 'done'
              AND m.subject IS NOT NULL
        """)


# ── 11. A/B Test Results ──────────────────────────────────────────────────────
class AmrAbReport(models.Model):
    _name = 'amr.ab.report'
    _description = 'A/B Test Results'
    _auto = False
    _rec_name = 'subject'
    _order = 'sent_date desc'

    mailing_id = fields.Many2one('mailing.mailing', string='Mailing', readonly=True)
    subject = fields.Char(string='Subject', readonly=True)
    ab_testing_enabled = fields.Boolean(string='A/B Test Enabled', readonly=True)
    ab_testing_pc = fields.Integer(string='A/B Test %', readonly=True)
    ab_testing_winner_selection = fields.Selection([
        ('manual', 'Manual'),
        ('clicks', 'Clicks'),
        ('open', 'Opens'),
        ('reply', 'Replies'),
    ], string='Winner Selection', readonly=True)
    ab_testing_completed = fields.Boolean(string='A/B Test Completed', readonly=True)
    is_winner = fields.Boolean(string='Is Winner', readonly=True)
    sent = fields.Integer(string='Sent', readonly=True)
    open_rate = fields.Float(string='Open %', readonly=True, digits=(16, 2))
    click_rate = fields.Float(string='Click %', readonly=True, digits=(16, 2))
    bounce_rate = fields.Float(string='Bounce %', readonly=True, digits=(16, 2))
    sent_date = fields.Datetime(string='Sent Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_ab_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_ab_report AS
            WITH click_per_mailing AS (
                SELECT mass_mailing_id, COUNT(*) AS cnt
                FROM mailing_trace
                WHERE trace_status = 'click'
                GROUP BY mass_mailing_id
            )
            SELECT
                m.id                                                                AS id,
                m.id                                                                AS mailing_id,
                m.subject                                                           AS subject,
                COALESCE(m.ab_testing_enabled,   FALSE)                             AS ab_testing_enabled,
                COALESCE(m.ab_testing_pc,        0)                                 AS ab_testing_pc,
                m.ab_testing_winner_selection                                       AS ab_testing_winner_selection,
                COALESCE(m.ab_testing_completed, FALSE)                             AS ab_testing_completed,
                COALESCE(m.ab_testing_is_winner_mailing, FALSE)                    AS is_winner,
                COALESCE(m.sent, 0)                                                 AS sent,
                ROUND(COALESCE(m.opened_ratio,  0)::numeric, 2)                    AS open_rate,
                ROUND(
                    COALESCE(cpm.cnt, 0)::numeric / NULLIF(m.sent, 0) * 100, 2
                )                                                                   AS click_rate,
                ROUND(COALESCE(m.bounced_ratio, 0)::numeric, 2)                    AS bounce_rate,
                m.sent_date                                                         AS sent_date
            FROM mailing_mailing m
            LEFT JOIN click_per_mailing cpm ON cpm.mass_mailing_id = m.id
            WHERE m.mailing_type = 'mail'
              AND m.ab_testing_enabled = TRUE
        """)


# ── 12. Automation Trigger Effectiveness ──────────────────────────────────────
class AmrTriggerReport(models.Model):
    _name = 'amr.trigger.report'
    _description = 'Automation Trigger Effectiveness'
    _auto = False
    _order = 'avg_open_rate desc'

    trigger_type = fields.Char(string='Trigger Type', readonly=True)
    activities_count = fields.Integer(string='Activities Count', readonly=True)
    total_sent = fields.Integer(string='Total Sent', readonly=True)
    avg_open_rate = fields.Float(string='Avg Open %', readonly=True, digits=(16, 2))
    avg_click_rate = fields.Float(string='Avg Click %', readonly=True, digits=(16, 2))
    avg_bounce_rate = fields.Float(string='Avg Bounce %', readonly=True, digits=(16, 2))

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_trigger_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_trigger_report AS
            WITH click_per_mailing AS (
                SELECT mass_mailing_id, COUNT(*) AS cnt
                FROM mailing_trace
                WHERE trace_status = 'click'
                GROUP BY mass_mailing_id
            )
            SELECT
                ROW_NUMBER() OVER (
                    ORDER BY AVG(COALESCE(mm.opened_ratio, 0)) DESC
                )                                                                AS id,
                COALESCE(a.trigger_type, 'begin')                               AS trigger_type,
                COUNT(a.id)                                                      AS activities_count,
                COALESCE(SUM(mm.sent), 0)                                        AS total_sent,
                ROUND(AVG(COALESCE(mm.opened_ratio,  0))::numeric, 2)           AS avg_open_rate,
                ROUND(AVG(
                    COALESCE(cpm.cnt,0)::numeric / NULLIF(mm.sent,0) * 100
                )::numeric, 2)                                                   AS avg_click_rate,
                ROUND(AVG(COALESCE(mm.bounced_ratio, 0))::numeric, 2)           AS avg_bounce_rate
            FROM marketing_activity a
            LEFT JOIN mailing_mailing mm  ON mm.id  = a.mass_mailing_id
            LEFT JOIN click_per_mailing cpm ON cpm.mass_mailing_id = mm.id
            WHERE a.activity_type = 'email'
            GROUP BY a.trigger_type
        """)


# ── 13. Contact Engagement Scoring ────────────────────────────────────────────
class AmrContactEngagement(models.Model):
    _name = 'amr.contact.engagement'
    _description = 'Contact Engagement Scoring'
    _auto = False
    _rec_name = 'email'
    _order = 'engagement_score desc'

    email = fields.Char(string='Email', readonly=True)
    total_received = fields.Integer(string='Total Received', readonly=True)
    total_opened = fields.Integer(string='Total Opened', readonly=True)
    total_clicked = fields.Integer(string='Total Clicked', readonly=True)
    total_bounced = fields.Integer(string='Total Bounced', readonly=True)
    open_rate = fields.Float(string='Open %', readonly=True, digits=(16, 2))
    click_rate = fields.Float(string='Click %', readonly=True, digits=(16, 2))
    engagement_score = fields.Float(string='Engagement Score', readonly=True, digits=(16, 2))
    engagement_tier = fields.Char(string='Tier', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_contact_engagement')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_contact_engagement AS
            WITH per_email AS (
                SELECT
                    t.email,
                    COUNT(*)                                                        AS total_received,
                    COUNT(*) FILTER (WHERE t.trace_status = 'open')                AS total_opened,
                    COUNT(*) FILTER (WHERE t.trace_status = 'click')               AS total_clicked,
                    COUNT(*) FILTER (WHERE t.trace_status = 'bounce')              AS total_bounced
                FROM mailing_trace t
                INNER JOIN mailing_mailing m ON m.id = t.mass_mailing_id
                WHERE t.email IS NOT NULL
                  AND t.email != ''
                  AND m.mailing_type = 'mail'
                GROUP BY t.email
            ),
            scored AS (
                SELECT
                    email,
                    total_received,
                    total_opened,
                    total_clicked,
                    total_bounced,
                    ROUND(
                        (total_opened::numeric  / NULLIF(total_received, 0)) * 100, 2
                    )                                                               AS open_rate,
                    ROUND(
                        (total_clicked::numeric / NULLIF(total_received, 0)) * 100, 2
                    )                                                               AS click_rate,
                    ROUND(GREATEST(0, LEAST(100, (
                        (total_opened::numeric  / NULLIF(total_received, 0)) * 100 * 0.5
                      + (total_clicked::numeric / NULLIF(total_received, 0)) * 100 * 0.4
                      - CASE WHEN total_bounced > 0 THEN 10 ELSE 0 END
                    )))::numeric, 2)                                                AS engagement_score
                FROM per_email
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY engagement_score DESC) AS id,
                email,
                total_received,
                total_opened,
                total_clicked,
                total_bounced,
                open_rate,
                click_rate,
                engagement_score,
                CASE
                    WHEN engagement_score >= 70 THEN 'Highly Engaged'
                    WHEN engagement_score >= 40 THEN 'Moderate'
                    ELSE 'Cold'
                END                                                                 AS engagement_tier
            FROM scored
        """)


# ── 14. Mailing List Health ───────────────────────────────────────────────────
class AmrListHealthReport(models.Model):
    _name = 'amr.list.health.report'
    _description = 'Mailing List Health'
    _auto = False
    _rec_name = 'list_name'
    _order = 'health_score desc'

    list_id = fields.Many2one('mailing.list', string='Mailing List', readonly=True)
    list_name = fields.Char(string='List Name', readonly=True)
    total_contacts = fields.Integer(string='Total Contacts', readonly=True)
    active_contacts = fields.Integer(string='Active', readonly=True)
    opted_out = fields.Integer(string='Opted Out', readonly=True)
    bounced_ever = fields.Integer(string='Bounced (ever)', readonly=True)
    active_pct = fields.Float(string='Active %', readonly=True, digits=(16, 2))
    health_score = fields.Float(string='Health Score', readonly=True, digits=(16, 2))
    health_badge = fields.Char(string='Health Badge', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_list_health_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_list_health_report AS
            WITH list_stats AS (
                SELECT
                    ml.id                                                           AS list_id,
                    ml.name                                                         AS list_name,
                    COUNT(sub.id)                                                   AS total_contacts,
                    COUNT(sub.id) FILTER (WHERE sub.opt_out = FALSE)                AS active_contacts,
                    COUNT(sub.id) FILTER (WHERE sub.opt_out = TRUE)                 AS opted_out
                FROM mailing_list ml
                LEFT JOIN mailing_contact_subscription sub ON sub.list_id = ml.id
                GROUP BY ml.id, ml.name
            ),
            bounce_stats AS (
                SELECT
                    sub.list_id,
                    COUNT(DISTINCT t.email)                                         AS bounced_ever
                FROM mailing_trace t
                INNER JOIN mailing_contact mc ON mc.email = t.email
                INNER JOIN mailing_contact_subscription sub ON sub.contact_id = mc.id
                WHERE t.trace_status = 'bounce'
                GROUP BY sub.list_id
            )
            SELECT
                ls.list_id                                                          AS id,
                ls.list_id,
                ls.list_name,
                COALESCE(ls.total_contacts,  0)                                     AS total_contacts,
                COALESCE(ls.active_contacts, 0)                                     AS active_contacts,
                COALESCE(ls.opted_out,       0)                                     AS opted_out,
                COALESCE(bs.bounced_ever,    0)                                     AS bounced_ever,
                ROUND(
                    (COALESCE(ls.active_contacts,0)::numeric
                     / NULLIF(ls.total_contacts, 0)) * 100, 2
                )                                                                   AS active_pct,
                ROUND(GREATEST(0, (
                    (COALESCE(ls.active_contacts, 0)::numeric
                     / NULLIF(ls.total_contacts, 0)) * 100
                  - (COALESCE(bs.bounced_ever, 0)::numeric
                     / NULLIF(ls.total_contacts, 0)) * 20
                ))::numeric, 2)                                                     AS health_score,
                CASE
                    WHEN (COALESCE(ls.active_contacts,0)::numeric
                          / NULLIF(ls.total_contacts,0)) * 100 >= 85
                        THEN 'Healthy'
                    WHEN (COALESCE(ls.active_contacts,0)::numeric
                          / NULLIF(ls.total_contacts,0)) * 100 >= 60
                        THEN 'Average'
                    ELSE 'Needs Cleaning'
                END                                                                 AS health_badge
            FROM list_stats ls
            LEFT JOIN bounce_stats bs ON bs.list_id = ls.list_id
            WHERE ls.total_contacts > 0
        """)


# ── 15. Re-engagement Opportunities ──────────────────────────────────────────
class AmrReengagementReport(models.Model):
    _name = 'amr.reengagement.report'
    _description = 'Re-engagement Opportunities'
    _auto = False
    _rec_name = 'email'
    _order = 'days_since_last_open desc'

    email = fields.Char(string='Email', readonly=True)
    last_opened = fields.Datetime(string='Last Opened', readonly=True)
    days_since_last_open = fields.Integer(string='Days Since Last Open', readonly=True)
    campaigns_since_last_open = fields.Integer(string='Campaigns Since Last Open', readonly=True)
    reengagement_status = fields.Char(string='Status', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_reengagement_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_reengagement_report AS
            WITH per_email AS (
                SELECT
                    email,
                    MAX(open_datetime)                      AS last_opened,
                    COUNT(DISTINCT mass_mailing_id)         AS total_campaigns
                FROM mailing_trace
                WHERE email IS NOT NULL
                  AND email != ''
                GROUP BY email
            ),
            campaigns_after_last_open AS (
                SELECT
                    t.email,
                    COUNT(DISTINCT t.mass_mailing_id)       AS campaigns_since
                FROM mailing_trace t
                INNER JOIN per_email pe ON pe.email = t.email
                WHERE (pe.last_opened IS NULL
                    OR t.sent_datetime > pe.last_opened)
                  AND t.open_datetime IS NULL
                GROUP BY t.email
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY pe.last_opened ASC NULLS FIRST) AS id,
                pe.email,
                pe.last_opened,
                EXTRACT(
                    DAY FROM NOW() - pe.last_opened
                )::int                                                       AS days_since_last_open,
                COALESCE(ca.campaigns_since, 0)                              AS campaigns_since_last_open,
                CASE
                    WHEN pe.last_opened IS NULL
                        THEN 'Lost'
                    WHEN NOW() - pe.last_opened > INTERVAL '90 days'
                        THEN 'Lost'
                    WHEN NOW() - pe.last_opened > INTERVAL '60 days'
                        THEN 'Dormant'
                    WHEN NOW() - pe.last_opened > INTERVAL '30 days'
                        THEN 'At Risk'
                    ELSE NULL
                END                                                          AS reengagement_status
            FROM per_email pe
            LEFT JOIN campaigns_after_last_open ca ON ca.email = pe.email
            WHERE (
                pe.last_opened IS NULL
                OR NOW() - pe.last_opened > INTERVAL '30 days'
            )
        """)
