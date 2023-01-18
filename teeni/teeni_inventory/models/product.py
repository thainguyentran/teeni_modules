from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api,osv, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import AccessError, UserError, ValidationError, Warning
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import logging
_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    average_cost_price = fields.Float(
        string='Average Cost', compute='_compute_avg_cost', readonly=True)
    teeni_status = fields.Selection([
        ('atv', 'Active'),
        ('dc', 'DC')
        ], string="Status", default='atv')

    pack_size = fields.Char()

    @api.onchange('id')
    def _compute_avg_cost(self):
        unit = 1
        total_cost = 0
        product_id = self.env["product.product"].search([('product_tmpl_id', '=', self.id)], limit=1)
        pol = self.env["purchase.order.line"].search([('product_id', '=', product_id.id)])
        if self.tracking == 'none':
            if pol:
                unit = 0
            for pol_id in pol:
                if pol_id.state == 'purchase':
                    unit += pol_id.product_qty
                    total_cost += (pol_id.price_unit * pol_id.product_qty)
        if unit > 0:
            self.average_cost_price = total_cost / unit
        else:
            self.average_cost_price = 0


