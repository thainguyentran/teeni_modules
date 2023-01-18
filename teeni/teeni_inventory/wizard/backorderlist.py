# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare

import logging
_logger = logging.getLogger(__name__)


class TeeniStockBackorderConfirmation(models.TransientModel):
    _name = 'teeni.stock.backorder.confirmation'
    _description = 'Teeni Backorder Confirmation'

    teeni_pick_ids = fields.Many2many('stock.picking', 'teeni_stock_picking_backorder_rel')
    move_ids = fields.One2many('stock.move', related='teeni_pick_ids.move_ids_without_package')
    bo_product = fields.Many2many('bo.remaining.product', compute='_get_bo_remaining_product')

    def _get_bo_remaining_product(self):
        lis_rec = []
        for line in self.move_ids:
            if line.product_uom_qty != line.quantity_done:
                dic={
                    'product_id':line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'quantity_done': line.quantity_done
                }
                obj = self.env['bo.remaining.product'].create(dic)
                lis_rec.append(obj.id)
        self.bo_product = [(6, 0, lis_rec)]

    @api.one
    def _process(self, cancel_backorder=False):
        if cancel_backorder:
            for pick_id in self.teeni_pick_ids:
                moves_to_log = {}
                for move in pick_id.move_lines:
                    if float_compare(move.product_uom_qty, move.quantity_done, precision_rounding=move.product_uom.rounding) > 0:
                        moves_to_log[move] = (move.quantity_done, move.product_uom_qty)
                pick_id._log_less_quantities_than_expected(moves_to_log)
        for pick in self.teeni_pick_ids:
            if pick.picking_type_name == 'Internal Transfers':
                pick.state = 'processed'
            else:
                self.teeni_pick_ids.action_done()

        if cancel_backorder:
            for pick_id in self.teeni_pick_ids:
                backorder_pick = self.env['stock.picking'].search([('backorder_id', '=', pick_id.id)])
                backorder_pick.action_cancel()
                pick_id.message_post(body=_("Back order <em>%s</em> <b>cancelled</b>.") % (",".join([b.name or '' for b in backorder_pick])))

    def process(self):
        # picking = self.env['stock.picking'].search([('id', '=', self.teeni_pick_ids.id)])
        # if picking.picking_type_name == "Delivery Orders":
        #     view = self.env.ref('teeni_inventory.assign_driver_view')
        #     wiz = self.env['assign.driver.wiz'].create({'teeni_pick_ids': [(4, p.id) for p in picking]})
        #     context = dict(self.env.context or {})
        #     context['active_id'] = picking.id
        #     return {
        #         'name': _('Assign Driver?'),
        #         'type': 'ir.actions.act_window',
        #         'view_type': 'form',
        #         'view_mode': 'form',
        #         'res_model': 'assign.driver.wiz',
        #         'views': [(view.id, 'form')],
        #         'view_id': view.id,
        #         'target': 'new',
        #         'res_id': wiz.id,
        #         'context': context,
        #     }
        self._process()

    def process_cancel_backorder(self):
        self._process(cancel_backorder=True)


class RemainingProduct(models.Model):
    _name = 'bo.remaining.product'

    product_id = fields.Many2one('product.product')
    product_uom_qty = fields.Float()
    quantity_done = fields.Float()


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'
    _description = 'Backorder Confirmation'

    @api.one
    def _process(self, cancel_backorder=False):
        if cancel_backorder:
            for pick_id in self.pick_ids:
                moves_to_log = {}
                for move in pick_id.move_lines:
                    if float_compare(move.product_uom_qty, move.quantity_done,
                                     precision_rounding=move.product_uom.rounding) > 0:
                        moves_to_log[move] = (move.quantity_done, move.product_uom_qty)
                if moves_to_log:
                    pick_id._log_less_quantities_than_expected(moves_to_log)
        for pick in self.pick_ids:
            if pick.picking_type_name == 'Internal Transfers':
                pick.state = 'processed'
            else:
                self.pick_ids.action_done()
        if cancel_backorder:
            for pick_id in self.pick_ids:
                backorder_pick = self.env['stock.picking'].search([('backorder_id', '=', pick_id.id)])
                backorder_pick.action_cancel()
                pick_id.message_post(body=_("Back order <em>%s</em> <b>cancelled</b>.") % (
                    ",".join([b.name or '' for b in backorder_pick])))
