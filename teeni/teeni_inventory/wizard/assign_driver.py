# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AssignDriver(models.TransientModel):
    _name = 'assign.driver.wiz'
    _description = 'Assign Driver DO'

    teeni_pick_ids = fields.Many2many('stock.picking', 'stock_picking_assign_driver_rel')
    driver_id = fields.Many2one('res.users', string="Driver Name")
    delivery_date = fields.Date()

    def process(self):
        for picking in self.teeni_pick_ids:
            self.check_delivery_date()
            picking.write({
                'assigned_driver_id': self.driver_id.id,
                'assigned_delivery_date': self.delivery_date,
                'is_out_for_delivery': True,
                'state': 'done'
            })
            self.teeni_pick_ids.action_done()
        return False

    def check_delivery_date(self):
        if self.delivery_date:
            if self.teeni_pick_ids.sale_id.po_term_id:
                if self.delivery_date >= self.teeni_pick_ids.sale_id.date_order.date() + timedelta(days=self.teeni_pick_ids.sale_id.po_term_id.days):
                    raise ValidationError(_("Delivery Date need to be within the PO Term."))