from odoo import api, fields, models


class SalePushDevice(models.Model):
    _name = 'sale.push_device'

    name = fields.Char(string='Device Name')
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Receiver', ondelete='cascade')
    mobile_id = fields.Char('Mobile ID')
