from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    adjustment_credit_account_id = fields.Many2one(
        'account.account',
        domain=[('deprecated', '=', False)])
    adjustment_debit_account_id = fields.Many2one(
        'account.account',
        domain=[('deprecated', '=', False)])
    sale_order_import_email = fields.Char(
        'Mail Gateway: Destination E-mail',
        help="This field is used in multi-company setups to import the "
        "invoices received by the mail gateway in the appropriate company")
    sale_order_import_create_bank_account = fields.Boolean(
        string='Auto-create Bank Account of Customer')

    _sql_constraints = [(
        'sale_order_import_email_uniq',
        'unique(sale_order_import_email)',
        'This sale order import email already exists!')]
