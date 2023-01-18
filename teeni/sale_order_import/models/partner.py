from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sale_order_import_ids = fields.One2many(
        'sale.order.import.config', 'partner_id',
        string='Sale Order Import Configuration')
    sale_order_import_count = fields.Integer(
        compute='_compute_sale_order_import_count',
        string='Number of Sale Order Import Configurations',
        readonly=True)

    def _compute_invoice_import_count(self):
        config_data = self.env['sale.order.import.config'].read_group(
            [('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        mapped_data = dict([
            (config['partner_id'][0], config['partner_id_count'])
            for config in config_data])
        for partner in self:
            partner.sale_order_import_count = mapped_data.get(partner.id, 0)
