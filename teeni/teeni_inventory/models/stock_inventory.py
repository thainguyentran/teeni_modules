from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError,Warning
from odoo.tools import float_utils, float_compare
import logging
_logger = logging.getLogger(__name__)


class Inventory(models.Model):
    _inherit = "stock.inventory"
    
    def action_validate(self):
        context = self._context
        current_uid = context.get('uid')
        user = self.env['res.users'].browse(current_uid)
        _logger.debug("VALIDATE FUCKING CREATE UID %s FUCKING USER %s", self.create_uid, user)
        if user != self.create_uid:
            raise Warning(_("You cannot validate IA of other users"))
        inventory_lines = self.line_ids.filtered(lambda l: l.product_id.tracking in ['lot', 'serial'] and not l.prod_lot_id and l.theoretical_qty != l.product_qty)
        lines = self.line_ids.filtered(lambda l: float_compare(l.product_qty, 1, precision_rounding=l.product_uom_id.rounding) > 0 and l.product_id.tracking == 'serial' and l.prod_lot_id)
        if inventory_lines and not lines:
            wiz_lines = [(0, 0, {'product_id': product.id, 'tracking': product.tracking}) for product in inventory_lines.mapped('product_id')]
            wiz = self.env['stock.track.confirmation'].create({'inventory_id': self.id, 'tracking_line_ids': wiz_lines})
            return {
                    'name': _('Tracked Products in Inventory Adjustment'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'stock.track.confirmation',
                    'target': 'new',
                    'res_id': wiz.id,
                }
        else:
            self._action_done()

    def action_cancel_draft(self):
        context = self._context
        current_uid = context.get('uid')
        user = self.env['res.users'].browse(current_uid)
        if user != self.create_uid:
            raise Warning(_("You cannot cancel IA of other users"))
        self.mapped('move_ids')._action_cancel()
        self.write({
            'line_ids': [(5,)],
            'state': 'draft'
        })


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    @api.model_create_multi
    def create(self, vals_list):
        context = self._context
        current_uid = context.get('uid')
        user = self.env['res.users'].browse(current_uid)
        for values in vals_list:
            c_uid = self.env['stock.inventory'].browse(values['inventory_id']).create_uid
            if user != c_uid:
                raise Warning(_("You cannot edit IA of other users"))
            if 'product_id' in values and 'product_uom_id' not in values:
                values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
        res = super(InventoryLine, self).create(vals_list)
        res._check_no_duplicate_line()
        return res

    @api.multi
    def write(self, vals):
        context = self._context
        current_uid = context.get('uid')
        user = self.env['res.users'].browse(current_uid)
        if user != self.create_uid or user != self.inventory_id.create_uid:
            raise Warning(_("You cannot edit IA of other users"))
        self._check_no_duplicate_line()
        return super(InventoryLine, self).write(vals)

