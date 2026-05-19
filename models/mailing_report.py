from odoo import fields, models, tools


class AmrMailingReport(models.Model):
    _name = 'amr.mailing.report'
    _description = 'Email Campaign Stats'
    _auto = False
    _rec_name = 'subject'
    _order = 'sent_date desc'

    mailing_id = fields.Many2one('mailing.mailing', string='Mailing', readonly=True)
    subject = fields.Char(string='Subject', readonly=True)
    email_from = fields.Char(string='From', readonly=True)
    mailing_type = fields.Selection([
        ('mail', 'Email'),
        ('sms', 'SMS'),
    ], string='Type', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_queue', 'In Queue'),
        ('sending', 'Sending'),
        ('done', 'Sent'),
    ], string='Status', readonly=True)
    sent_date = fields.Datetime(string='Sent Date', readonly=True)
    schedule_date = fields.Datetime(string='Scheduled Date', readonly=True)

    total = fields.Integer(string='Total', readonly=True)
    sent = fields.Integer(string='Sent', readonly=True)
    delivered = fields.Integer(string='Delivered', readonly=True)
    opened = fields.Integer(string='Opened', readonly=True)
    clicked = fields.Integer(string='Clicked', readonly=True)
    replied = fields.Integer(string='Replied', readonly=True)
    bounced = fields.Integer(string='Bounced', readonly=True)
    failed = fields.Integer(string='Failed', readonly=True)
    canceled = fields.Integer(string='Canceled', readonly=True)

    open_rate = fields.Float(string='Open %', readonly=True, digits=(16, 2))
    click_rate = fields.Float(string='Click %', readonly=True, digits=(16, 2))
    bounce_rate = fields.Float(string='Bounce %', readonly=True, digits=(16, 2))
    delivery_rate = fields.Float(string='Delivery %', readonly=True, digits=(16, 2))
    reply_rate = fields.Float(string='Reply %', readonly=True, digits=(16, 2))

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_mailing_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_mailing_report AS
            WITH click_stats AS (
                SELECT mass_mailing_id, COUNT(*) AS cnt
                FROM mailing_trace
                WHERE trace_status = 'click'
                GROUP BY mass_mailing_id
            ),
            cancel_stats AS (
                SELECT mass_mailing_id, COUNT(*) AS cnt
                FROM mailing_trace
                WHERE trace_status = 'cancel'
                GROUP BY mass_mailing_id
            )
            SELECT
                m.id                                                                    AS id,
                m.id                                                                    AS mailing_id,
                m.subject                                                               AS subject,
                m.email_from                                                            AS email_from,
                m.mailing_type                                                          AS mailing_type,
                m.state                                                                 AS state,
                m.sent_date                                                             AS sent_date,
                m.schedule_date                                                         AS schedule_date,
                COALESCE(m.expected,  0)                                                AS total,
                COALESCE(m.sent,      0)                                                AS sent,
                GREATEST(0, COALESCE(m.sent, 0) - COALESCE(m.bounced, 0))             AS delivered,
                COALESCE(m.opened,    0)                                                AS opened,
                COALESCE(cs.cnt,      0)                                                AS clicked,
                COALESCE(m.replied,   0)                                                AS replied,
                COALESCE(m.bounced,   0)                                                AS bounced,
                COALESCE(m.failed,    0)                                                AS failed,
                COALESCE(cc.cnt,      0)                                                AS canceled,
                ROUND(COALESCE(m.opened_ratio,    0)::numeric, 2)                      AS open_rate,
                ROUND((COALESCE(cs.cnt, 0)::numeric
                    / NULLIF(m.sent, 0)) * 100, 2)                                     AS click_rate,
                ROUND(COALESCE(m.bounced_ratio,   0)::numeric, 2)                      AS bounce_rate,
                ROUND(COALESCE(m.received_ratio,  0)::numeric, 2)                      AS delivery_rate,
                ROUND(COALESCE(m.replied_ratio,   0)::numeric, 2)                      AS reply_rate
            FROM mailing_mailing m
            LEFT JOIN click_stats  cs ON cs.mass_mailing_id  = m.id
            LEFT JOIN cancel_stats cc ON cc.mass_mailing_id  = m.id
            WHERE m.mailing_type = 'mail'
        """)


class AmrMailTraceReport(models.Model):
    _name = 'amr.mail.trace.report'
    _description = 'Email Delivery Details'
    _auto = False
    _rec_name = 'email'
    _order = 'sent_datetime desc'

    trace_id = fields.Integer(string='Trace ID', readonly=True)
    mailing_id = fields.Many2one('mailing.mailing', string='Mailing', readonly=True)
    email = fields.Char(string='Recipient Email', readonly=True)
    trace_status = fields.Selection([
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('open', 'Opened'),
        ('reply', 'Replied'),
        ('click', 'Clicked'),
        ('cancel', 'Canceled'),
        ('bounce', 'Bounced'),
        ('error', 'Error'),
    ], string='Status', readonly=True)
    failure_type = fields.Selection([
        ('unknown', 'Unknown Error'),
        ('mail_email_invalid', 'Invalid Email Address'),
        ('mail_email_missing', 'Missing Email'),
        ('mail_from_missing', 'Missing From'),
        ('mail_from_invalid', 'Invalid From'),
        ('mail_bounce', 'Email Bounced'),
        ('mail_bl', 'Blacklisted Address'),
        ('mail_optout', 'Opted Out'),
        ('mail_dup', 'Duplicate'),
        ('sms_number_missing', 'Missing SMS Number'),
        ('sms_number_format_wrong', 'Wrong SMS Format'),
        ('sms_country_not_supported', 'SMS Country Not Supported'),
        ('sms_registration_needed', 'SMS Registration Required'),
        ('sms_credit', 'Insufficient SMS Credits'),
        ('sms_server', 'SMS Server Error'),
        ('sms_acc', 'Unlinked SMS Account'),
        ('sms_blacklist', 'SMS Blacklisted'),
        ('sms_customer_error', 'SMS Customer Error'),
        ('sms_rejected', 'SMS Rejected'),
    ], string='Failure Reason', readonly=True)
    sent_datetime = fields.Datetime(string='Sent On', readonly=True)
    open_datetime = fields.Datetime(string='Opened On', readonly=True)
    clicked_datetime = fields.Datetime(string='Clicked On', readonly=True)
    replied_datetime = fields.Datetime(string='Replied On', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'amr_mail_trace_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW amr_mail_trace_report AS
            SELECT
                t.id                        AS id,
                t.id                        AS trace_id,
                t.mass_mailing_id           AS mailing_id,
                t.email                     AS email,
                t.trace_status              AS trace_status,
                t.failure_type              AS failure_type,
                t.sent_datetime             AS sent_datetime,
                t.open_datetime             AS open_datetime,
                t.links_click_datetime      AS clicked_datetime,
                t.reply_datetime            AS replied_datetime
            FROM mailing_trace t
            INNER JOIN mailing_mailing m ON m.id = t.mass_mailing_id
            WHERE m.mailing_type = 'mail'
        """)
