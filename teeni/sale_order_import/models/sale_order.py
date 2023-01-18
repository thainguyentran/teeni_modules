from odoo import models, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def name_get(self):
        """Add amount_untaxed in name_get of invoices"""
        res = super().name_get()
        if self.env.context.get('sale_order_show_amount'):
            new_res = []
            for (sale_order_id, name) in res:
                sale_order = self.browse(sale_order_id)
                # I didn't find a python method to easily display
                # a float + currency symbol (before or after)
                # depending on lang of context and currency
                name += _(' Amount w/o tax: %s %s') % (
                    sale_order.amount_untaxed, sale_order.currency_id.name)
                new_res.append((sale_order_id, name))
            return new_res
        return res
