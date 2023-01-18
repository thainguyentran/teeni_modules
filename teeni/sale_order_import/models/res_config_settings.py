from odoo import models, fields


class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    adjustment_credit_account_id = fields.Many2one(
        related='company_id.adjustment_credit_account_id', readonly=False)
    adjustment_debit_account_id = fields.Many2one(
        related='company_id.adjustment_debit_account_id', readonly=False)
    sale_order_import_email = fields.Char(
        related='company_id.sale_order_import_email', readonly=False)
    sale_order_import_create_bank_account = fields.Boolean(
        related='company_id.sale_order_import_create_bank_account',
        readonly=False)
