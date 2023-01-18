from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar


class PickingSummaryReport(models.TransientModel):
    _name = 'teeni.picking.summary.wiz'

    picking_id = fields.Many2many('stock.picking')
    location_id = fields.Many2one('stock.location')
    po_id = fields.Many2one('sale.order', string="Po No")

    rec_lines = fields.Many2many('teeni.summary.picking.detail')

    def run_process(self):
        list_rec = []
        pd_list = []

        filter_val = [('picking_id', 'in', list(self.picking_id.ids))]
        if self.location_id:
            filter_val.append(tuple(['location_id', '=', self.location_id.id]))
        if self.po_id:
            filter_val.append(tuple(['picking_id.sale_id', '=', self.po_id.id]))

        ml_obj = self.env['stock.move.line'].search(filter_val, order="location_id desc")

        chk = 0
        for ml in ml_obj:
            for rec in pd_list:
                if rec['picking_id'] == ml.picking_id.id and rec['product_id'] == ml.product_id.id and rec['lot_id'] == ml.lot_id.id and rec['location_id'] == ml.location_id.id:
                    chk = 1
                    rec['quantity'] = rec['quantity'] + ml.qty

            if chk == 0:
                pd_list.append({
                    'picking_id': ml.picking_id.id,
                    'product_id': ml.product_id.id,
                    'quantity': ml.qty_done,
                    'product_uom_id': ml.product_uom_id.id,
                    'lot_id': ml.lot_id.id,
                    'location_id': ml.location_id.id,
                    'order_id': ml.picking_id.sale_id.id,
                })
        print("PL", pd_list)

        pick_obj = self.env['teeni.summary.picking.detail']
        for rec in pd_list:

            in_out_obj = self.env['teeni.summary.picking.detail'].create(rec)
            list_rec.append(in_out_obj.id)
            pick_obj += self.env['teeni.summary.picking.detail'].browse(in_out_obj.id)

        self.rec_lines = [(6, 0, list_rec)]

        return pick_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_inventory.action_picking_summary_pdf').report_action(self)


class PickingSummaryProduct(models.Model):
    _name = 'teeni.summary.picking.detail'

    picking_id  = fields.Many2one('stock.picking', string="Picking")
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float()
    product_uom_id = fields.Many2one('uom.uom', string="UOM")
    lot_id = fields.Many2one('stock.production.lot', string="Lot #")
    location_id = fields.Many2one('stock.location')
    order_id = fields.Many2one('sale.order', string="PO No")
