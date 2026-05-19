from odoo import fields, models, tools


class AmrCampaignReport(models.Model):
    _name = 'amr.campaign.report'
    _description = 'Marketing Automation Campaign Overview'
    _auto = False
    _rec_name = 'campaign_name'
    _order = 'create_date desc'

    campaign_id = fields.Many2one('marketing.campaign', string='Campaign', readonly=True)
    campaign_name = fields.Char(string='Campaign Name', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('stopped', 'Stopped'),
    ], string='Status', readonly=True)
    create_date = fields.Datetime(string='Created', readonly=True)
    last_sync_date = fields.Datetime(string='Last Sync', readonly=True)

    total_participants = fields.Integer(string='Total Participants', readonly=True)
    active_participants = fields.Integer(string='Active', readonly=True)
    completed_participants = fields.Integer(string='Completed', readonly=True)
    test_participants = fields.Integer(string='Test', readonly=True)

    email_activities = fields.Integer(string='Email Activities', readonly=True)

    open_rate = fields.Float(string='Open %', readonly=True, digits=(16, 2))
    delivery_rate = fields.Float(string='Delivery %', readonly=True, digits=(16, 2))
    bounce_rate = fields.Float(string='Bounce %', readonly=True, digits=(16, 2))
    reply_rate = fields.Float(string='Reply %', readonly=True, digits=(16, 2))

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_campaign_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_campaign_report AS
            SELECT
                c.id                                                                AS id,
                c.id                                                                AS campaign_id,
                c.name                                                              AS campaign_name,
                c.state                                                             AS state,
                c.create_date                                                       AS create_date,
                c.last_sync_date                                                    AS last_sync_date,
                COALESCE(p_all.cnt,  0)                                             AS total_participants,
                COALESCE(p_run.cnt,  0)                                             AS active_participants,
                COALESCE(p_done.cnt, 0)                                             AS completed_participants,
                COALESCE(p_test.cnt, 0)                                             AS test_participants,
                COALESCE(act.email_cnt, 0)                                          AS email_activities,
                ROUND(COALESCE(stats.open_rate,     0)::numeric, 2)                AS open_rate,
                ROUND(COALESCE(stats.delivery_rate, 0)::numeric, 2)                AS delivery_rate,
                ROUND(COALESCE(stats.bounce_rate,   0)::numeric, 2)                AS bounce_rate,
                ROUND(COALESCE(stats.reply_rate,    0)::numeric, 2)                AS reply_rate
            FROM marketing_campaign c
            LEFT JOIN (
                SELECT campaign_id, COUNT(*) AS cnt
                FROM marketing_participant
                GROUP BY campaign_id
            ) p_all ON p_all.campaign_id = c.id
            LEFT JOIN (
                SELECT campaign_id, COUNT(*) AS cnt
                FROM marketing_participant
                WHERE state = 'running'
                GROUP BY campaign_id
            ) p_run ON p_run.campaign_id = c.id
            LEFT JOIN (
                SELECT campaign_id, COUNT(*) AS cnt
                FROM marketing_participant
                WHERE state = 'completed'
                GROUP BY campaign_id
            ) p_done ON p_done.campaign_id = c.id
            LEFT JOIN (
                SELECT campaign_id, COUNT(*) AS cnt
                FROM marketing_participant
                WHERE is_test = TRUE
                GROUP BY campaign_id
            ) p_test ON p_test.campaign_id = c.id
            LEFT JOIN (
                SELECT campaign_id, COUNT(*) AS email_cnt
                FROM marketing_activity
                WHERE activity_type = 'email'
                GROUP BY campaign_id
            ) act ON act.campaign_id = c.id
            LEFT JOIN (
                SELECT
                    ma.campaign_id,
                    AVG(COALESCE(mm.opened_ratio,   0)) AS open_rate,
                    AVG(COALESCE(mm.received_ratio, 0)) AS delivery_rate,
                    AVG(COALESCE(mm.bounced_ratio,  0)) AS bounce_rate,
                    AVG(COALESCE(mm.replied_ratio,  0)) AS reply_rate
                FROM marketing_activity ma
                INNER JOIN mailing_mailing mm ON mm.id = ma.mass_mailing_id
                WHERE ma.activity_type = 'email'
                GROUP BY ma.campaign_id
            ) stats ON stats.campaign_id = c.id
        """)


class AmrActivityReport(models.Model):
    _name = 'amr.activity.report'
    _description = 'Marketing Automation Activity Stats'
    _auto = False
    _rec_name = 'activity_name'
    _order = 'campaign_id, activity_name'

    activity_id = fields.Many2one('marketing.activity', string='Activity', readonly=True)
    campaign_id = fields.Many2one('marketing.campaign', string='Campaign', readonly=True)
    activity_name = fields.Char(string='Activity Name', readonly=True)
    activity_type = fields.Selection([
        ('email', 'Email'),
        ('action', 'Server Action'),
    ], string='Type', readonly=True)
    trigger_type = fields.Selection([
        ('begin', 'Beginning of Campaign'),
        ('mail_open', 'Mail Opened'),
        ('mail_not_open', 'Mail Not Opened'),
        ('mail_reply', 'Mail Replied'),
        ('mail_not_reply', 'Mail Not Replied'),
        ('mail_click', 'Mail Clicked'),
        ('mail_not_click', 'Mail Not Clicked'),
        ('mail_bounce', 'Mail Bounced'),
        ('activity', 'Another Activity'),
    ], string='Trigger', readonly=True)
    interval_number = fields.Integer(string='Delay Number', readonly=True)
    interval_type = fields.Selection([
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Delay Type', readonly=True)

    sent = fields.Integer(string='Sent', readonly=True)
    opened = fields.Integer(string='Opened', readonly=True)
    clicked = fields.Integer(string='Clicked', readonly=True)
    bounced = fields.Integer(string='Bounced', readonly=True)
    replied = fields.Integer(string='Replied', readonly=True)
    processed = fields.Integer(string='Processed', readonly=True)
    rejected = fields.Integer(string='Rejected', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_activity_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_activity_report AS
            SELECT
                a.id                                AS id,
                a.id                                AS activity_id,
                a.campaign_id                       AS campaign_id,
                a.name                              AS activity_name,
                a.activity_type                     AS activity_type,
                a.trigger_type                      AS trigger_type,
                a.interval_number                   AS interval_number,
                a.interval_type                     AS interval_type,
                COALESCE(mm.sent,       0)          AS sent,
                COALESCE(mm.opened,     0)          AS opened,
                COALESCE(a.total_click, 0)          AS clicked,
                COALESCE(a.total_bounce,0)          AS bounced,
                COALESCE(mm.replied,    0)          AS replied,
                COALESCE(a.processed,   0)          AS processed,
                COALESCE(a.rejected,    0)          AS rejected
            FROM marketing_activity a
            LEFT JOIN mailing_mailing mm ON mm.id = a.mass_mailing_id
        """)


class AmrParticipantReport(models.Model):
    _name = 'amr.participant.report'
    _description = 'Marketing Automation Participant Breakdown'
    _auto = False
    _order = 'campaign_id, state'

    campaign_id = fields.Many2one('marketing.campaign', string='Campaign', readonly=True)
    state = fields.Selection([
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('removed', 'Removed'),
    ], string='State', readonly=True)
    is_test = fields.Boolean(string='Test', readonly=True)
    create_date = fields.Datetime(string='Entered On', readonly=True)
    participant_count = fields.Integer(string='Count', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_participant_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_participant_report AS
            SELECT
                ROW_NUMBER() OVER (
                    ORDER BY campaign_id, state, is_test, DATE(create_date)
                )                               AS id,
                campaign_id                     AS campaign_id,
                state                           AS state,
                is_test                         AS is_test,
                DATE(create_date)::timestamp    AS create_date,
                COUNT(*)                        AS participant_count
            FROM marketing_participant
            GROUP BY campaign_id, state, is_test, DATE(create_date)
        """)
