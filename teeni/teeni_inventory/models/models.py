# -*- coding: utf-8 -*-
import json
import time
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, osv, _

from odoo.exceptions import AccessError, UserError, ValidationError, Warning
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, etree
from odoo.tools.float_utils import float_round, float_compare, float_is_zero
from odoo.addons import decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    api.onchange('scheduled_date')

    def _check_scheduled_date(self):
        curr_date = self.scheduled_date
        if not self.sale_id:
            self.scheduled_date = curr_date

    count_picking_delivery = fields.Integer(compute='_compute_picking_count')

    def _compute_picking_count(self):
        # TDE TODO count picking can be done using previous two
        domains = {
            'count_picking_draft': [('state', '=', 'draft')],
            'count_picking_waiting': [('state', 'in', ('confirmed', 'waiting'))],
            'count_picking_ready': [('state', '=', 'assigned')],
            'count_picking': [('state', 'in', ('assigned', 'waiting', 'confirmed'))],
            'count_picking_late': [('scheduled_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', 'in', ('assigned', 'waiting', 'confirmed'))],
            'count_picking_backorders': [('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting'))],
            'count_picking_delivery': [('state', '=', 'done')]
        }
        for field in domains:
            data = self.env['stock.picking'].read_group(domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['picking_type_id'])
            count = {
                x['picking_type_id'][0]: x['picking_type_id_count']
                for x in data if x['picking_type_id']
            }
            for record in self:
                record[field] = count.get(record.id, 0)
        for record in self:
            record.rate_picking_late = record.count_picking and record.count_picking_late * 100 / record.count_picking or 0
            record.rate_picking_backorders = record.count_picking and record.count_picking_backorders * 100 / record.count_picking or 0

    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
        result = super(PickingType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                        submenu=submenu)
        print(view_type, "Res", result)
        if view_type == 'kanban':
            user = self.env.user
            picking = self.env['stock.picking'].sudo().search([])

            pickright = False
            if (user.has_group('teeni_inventory.group_packer_rights')
                and user.has_group('teeni_inventory.group_warehouse_assist_rights')
                and user.has_group('teeni_inventory.group_logistic_assist_rights')
                and user.has_group('stock.group_stock_manager')):
                pickright = True

            true_id = []
            false_id = []

            if pickright or user.has_group('teeni_inventory.group_can_process_picking'):
                query = "update stock_picking set can_view='True' where (can_view='False' or can_view is null)"
                self._cr.execute(query)
            else:
                for rec in picking:
                    if rec.picking_type_name == "Pick" and self.env.uid not in rec.packer_id.ids:
                        false_id.append(rec.id)
                        # rec.sudo().write({"can_view": False})
                    else:
                        true_id.append(rec.id)
                        # rec.sudo().write({"can_view": True})
                query = "update stock_picking set can_view='True' where id in " + str(tuple(true_id))
                self._cr.execute(query)
                query = "update stock_picking set can_view='False' where id in " + str(tuple(false_id))
                self._cr.execute(query)

        return result

class StockMove(models.Model):
    _inherit = "stock.move"

    available_qty = fields.Float(string="Available Qty", store=True)
    rec_lot_number = fields.Many2many('stock.production.lot', string="Rec Lot Number")
    have_lot = fields.Boolean(string="Have Lot Number?", default=False, store=True)
    pack_size = fields.Char(related='product_id.product_tmpl_id.pack_size')

    @api.onchange('product_id')
    def onchange_product_id(self):
        product = self.product_id.with_context(lang=self.partner_id.lang or self.env.user.lang)
        total_avail = self.env['stock.quant']._get_available_quantity(self.product_id,
                                                                      self.location_id) if self.product_id else 0.0
        check_lot = self.env['stock.production.lot'].search([('product_id', '=', product.id)],limit=1)
        self.name = product.partner_ref
        self.product_uom = product.uom_id.id
        self.available_qty = total_avail

        if total_avail and check_lot:
            self.have_lot = True
        return {'domain': {'product_uom': [('category_id', '=', product.uom_id.category_id.id)]}}

    reserved_availability = fields.Float(
        'Quantity Reserved', compute='_compute_reserved_availability',
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=False, store=True, help='Quantity that has already been reserved for this move')

    teeni_remarks = fields.Char(string="Remarks")
    rec_lot_number_name = fields.Char(compute="compute_lot_no")

    def compute_lot_no(self):
        for rec in self:
            lot_no_name = ""
            for lot in rec.rec_lot_number:
                lot_no_name += lot.name + ","
            if lot_no_name:
                lot_no_name = lot_no_name[:-1]
            rec.rec_lot_number_name = lot_no_name


    def unlink(self):
        if any(move.state not in ('draft', 'cancel', 'assigned', 'waiting', 'confirmed') for move in self):
            raise UserError(_('You can only delete draft moves.'))
        # With the non plannified picking, draft moves could have some move lines.
        self.mapped('move_line_ids').unlink()
        return models.Model.unlink(self)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    packer_sup_id = fields.Many2one(
        'res.users',
        string='Submitted by',
        readonly=True,
        copy=False,
    )

    packer_sup_date = fields.Date(
        string="Submitted date",
        readonly=True,
        copy=False,
    )

    manager_approved_id = fields.Many2one(
        'res.users',
        string='Approved by',
        readonly=True,
        copy=False,
    )

    manager_approved_date = fields.Date(
        string="Approved date",
        readonly=True,
        copy=False,
    )

    wh_process_id = fields.Many2one(
        'res.users',
        string='Processed by',
        readonly=True,
        copy=False,
    )

    wh_process_date = fields.Date(
        string="Processed date",
        readonly=True,
        copy=False,
    )

    packer_confirm_id = fields.Many2one(
        'res.users',
        string='Confirm received by',
        readonly=True,
        copy=False,
    )

    packer_confirm_date = fields.Date(
        string="Confirm received date",
        readonly=True,
        copy=False,
    )

    reject_id = fields.Many2one(
        'res.users',
        string='Rejected by',
        readonly=True,
        copy=False,
    )

    reject_date = fields.Date(
        string="Rejected date",
        readonly=True,
        copy=False,
    )

    packed_id = fields.Many2one(
        'res.users',
        string='Packed by',
        readonly=True,
        copy=False,
    )

    packed_date = fields.Date(
        string="Packed date",
        readonly=True,
        copy=False,
    )

    receipt_verified_id = fields.Many2one(
        'res.users',
        string='Receipt Verified by',
        readonly=True,
        copy=False,
    )

    receipt_verified_date = fields.Date(
        string="Receipt Verified date",
        readonly=True,
        copy=False,
    )

    pack_verified_id = fields.Many2one(
        'res.users',
        string='Pack Verified by',
        readonly=True,
        copy=False,
    )

    pack_verified_date = fields.Date(
        string="Pack Verified date",
        readonly=True,
        copy=False,
    )

    # driver_id = fields.Many2one(
    #     'res.users',
    #     string='Delivered by',
    #     readonly=True,
    #     copy=False,
    # )

    driver_picked_date = fields.Date(
        string="Driver Picked date",
        readonly=True,
        copy=False,
    )

    assigned_driver_id = fields.Many2one(
        'res.users',
        string='Assigned to',
        readonly=True,
        copy=False,
    )

    assigned_delivery_date = fields.Date(
        string="Assigned delivery date",
        copy=False,
    )

    deliver_confirm_date = fields.Date(
        string="Delivered date",
        readonly=True,
        copy=False,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('submitted', 'Request Submitted'),
        ('approved', 'Manager Approved'),
        ('processed', 'WH Assist Processed'),
        # ('packed', 'Items Packed'),
        ('verified', 'Verified'),
        # ('delivery', 'Out For Delivery'),
        ('done', 'Done/Out For Delivery'),
        ('cancel', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('s_rejected', 'Store Rejected'),
        ('f_delivery', 'Failed Delivery'),
        ('delivery_d', 'Delivered')

    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed.\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows).\n"
             " * Waiting: if it is not ready to be sent because the required products could not be reserved.\n"
             " * Ready: products are reserved and ready to be sent. If the shipping policy is 'As soon as possible' this happens as soon as anything is reserved.\n"
             " * Done: has been processed, can't be modified or cancelled anymore.\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore.")
    picking_type_name = fields.Char(related='picking_type_id.name', readonly=True)

    store_code = fields.Char(related='partner_id.store_code', compute='_get_store_code', string="Store Code")
    store_name = fields.Char(related='partner_id.name', compute='_get_store_code', string="Store Name")
    cus_po_num = fields.Char(string='Customer PO Number', related='sale_id.cus_po_num')
    teeni_delivery_date = fields.Date(string="Last Day of Delivery", related='sale_id.teeni_delivery_date')

    can_view = fields.Boolean(default="True")
    is_out_for_delivery = fields.Boolean(default="False")


    @api.depends('move_type', 'move_lines.state', 'move_lines.picking_id')
    @api.one
    def _compute_state(self):
        ''' State of a picking depends on the state of its related stock.move
        - Draft: only used for "planned pickings"
        - Waiting: if the picking is not ready to be sent so if
          - (a) no quantity could be reserved at all or if
          - (b) some quantities could be reserved and the shipping policy is "deliver all at once"
        - Waiting another move: if the picking is waiting for another move
        - Ready: if the picking is ready to be sent so if:
          - (a) all quantities are reserved or if
          - (b) some quantities could be reserved and the shipping policy is "as soon as possible"
        - Done: if the picking is done.
        - Cancelled: if the picking is cancelled
        '''
        if not self.move_lines:
            if self.picking_type_name in ['Pick','Delivery Orders']:
                self.state = 'cancel'
            else:
                self.state = 'draft'
        elif any(move.state == 'draft' for move in self.move_lines):  # TDE FIXME: should be all ?
            self.state = 'draft'
        elif all(move.state == 'cancel' for move in self.move_lines):
            self.state = 'cancel'
        elif all(move.state in ['cancel', 'done'] for move in self.move_lines):
            self.state = 'done'
        else:
            relevant_move_state = self.move_lines._get_relevant_state_among_moves()
            if relevant_move_state == 'partially_available':
                self.state = 'assigned'
            else:
                self.state = relevant_move_state

    @api.onchange('partner_id')
    def _get_store_code(self):
        self.store_code = self.partner_id.store_code
        self.store_name = self.partner_id.name

    @api.multi
    def write(self, values):
        for rec in self:
            if 'partner_id' in values.keys() and self.sale_id:
                self._cr.execute("update stock_picking set partner_id='"+str(values['partner_id'])+"' where sale_id='"+str(self.sale_id.id)+"'")
            context = self._context
            current_uid = context.get('uid')
            user = self.env['res.users'].browse(current_uid)
            print("User -->", user.id, "rec", rec.state)
            if user.has_group('teeni_inventory.group_driver_rights'):
                print("teeni_inventory.group_driver_rights")

            if ((user.has_group('teeni_inventory.group_packer_rights')) and (
                rec.state in ['confirmed', 'draft', 'submitted', 'processed', 'assigned', 'done', 'rejected'])):
                continue
            elif ((user.has_group('teeni_inventory.group_operation_manager_rights')) and (
                rec.state in ['submitted', 'approved','cancel'])):
                continue
            elif ((user.has_group('teeni_inventory.group_warehouse_assist_rights')) and (
                rec.state in ['assigned', 'processed', 'approved','done','verified','cancel'])):
                continue
            elif ((user.has_group('teeni_inventory.group_driver_rights')) and (
                rec.state in ['verified', 'done', 'delivery_d', 's_rejected', 'f_delivery'])):
                
                continue
            elif ((user.has_group('teeni_inventory.group_logistic_assist_rights')) and (
                rec.state in ['assigned','confirmed', 'done','cancel','s_rejected','f_delivery'])):
                continue
            elif (user.has_group('teeni_inventory.group_manager_rights')
                or user.has_group('teeni_inventory.group_sale_supervisor')
                and (rec.state in ['done','assgined'])):
                continue
            elif rec.state == 'waiting':
                continue
            elif rec.backorder_id and rec.state == "cancel":
                continue
            elif "can_view" in values:
                continue
            else:
                if self.create_uid:
                   if not (self.env.uid == self.create_uid.id) and rec.state != 'draft':
                    print("Record State", rec.state, rec.picking_type_id.name, rec.name)
                    raise Warning(_("You don't have the permission to edit this Picking"))
        return super(StockPicking, self).write(values)

    @api.onchange('assigned_delivery_date')
    def _check_changer(self):
        if not (self.env.user.has_group('teeni_inventory.group_logistic_assist_rights') or self.env.user.has_group('teeni_inventory.group_manager_rights')
                   or self.env.user.has_group('teeni_inventory.group_operation_manager_rights')) and self.picking_type_name == 'Delivery Orders':
            raise Warning(_("You dont have the right to change delivery date"))

    def packer_submit(self):
        user = self.env.user
        for rec in self:
            rec.packer_sup_date = fields.Date.today()
            rec.packer_sup_id = user.id
            if not user.has_group('teeni_inventory.group_packer_rights'):
                raise Warning(_("Only Packer can submit request"))
            for move_id in rec.move_ids_without_package:
                if move_id.quantity_done != 0:
                    raise Warning(_("Only WH Assist can move products"))
            for line in rec.move_line_ids_without_package:
                if line.qty_done != 0:
                    raise Warning(_("Only WH Assist can move products"))
            rec.state = 'submitted'
        subject = "Internal Transfer Request Submitted by " + str(user.partner_id.name)
        body = "Internal Transfer " + rec.name + " have been submitted by" + str(user.partner_id.name)
        notification = (
                           '<div class="stock.picking"><a href="#" class="o_redirect" data-oe-id="%s"></a></div>') % (
                           rec.name)
        post_vars = {'subject': subject, 'body': notification + body, }
        rec.message_post(type="notification", subtype="mail.mt_comment",
                       needaction_partner_ids=[(user.partner_id.id)], **post_vars)
        packer_submit_email = self.env.ref('teeni_inventory.email_packer_submit_template')
        packer_submit_email.send_mail(self.id)

    def manager_approve(self):
        user = self.env.user
        for rec in self:
            rec.manager_approved_date = fields.Date.today()
            rec.manager_approved_id = user.id
            if not user.has_group('teeni_inventory.group_operation_manager_rights'):
                raise Warning(_("Only Manager/Director can Approve request"))
            for move_id in rec.move_ids_without_package:
                if move_id.quantity_done != 0:
                    raise Warning(_("Only WH Assist can move products"))
            for line in rec.move_line_ids_without_package:
                if line.qty_done != 0:
                    raise Warning(_("Only WH Assist can move products"))
            rec.state = 'approved'
        subject = "Internal Transfer Request Approved by " + str(user.partner_id.name)
        body = "Internal Transfer " + rec.name + " have been approved by" + str(user.partner_id.name)
        notification = (
                           '<div class="stock.picking"><a href="#" class="o_redirect" data-oe-id="%s"></a></div>') % (
                           rec.name)
        post_vars = {'subject': subject, 'body': notification + body, }
        rec.message_post(type="notification", subtype="mail.mt_comment",
                       needaction_partner_ids=[(user.partner_id.id)], **post_vars)
        manager_approved_email = self.env.ref('teeni_inventory.manager_approved_template')
        manager_approved_email.send_mail(self.id)

    #button confirm received
    def packer_confirm(self):
        user = self.env.user
        for rec in self:
            rec.packer_confirm_date = fields.Date.today()
            rec.packer_confirm_id = user.id
            if not user.has_group('teeni_inventory.group_packer_rights'):
                raise Warning(_("Only Packer can confirm Receiving Items"))
        self.action_done()

        subject = "Internal Transfer Request Item Confirm Received by " + str(user.partner_id.name)
        body = "Internal Transfer " + rec.name + " have been confirm received by " + str(user.partner_id.name)
        notification = (
                           '<div class="stock.picking"><a href="#" class="o_redirect" data-oe-id="%s"></a></div>') % (
                           rec.name)
        post_vars = {'subject': subject, 'body': notification + body, }
        rec.message_post(type="notification", subtype="mail.mt_comment",
                       needaction_partner_ids=[(user.partner_id.id)], **post_vars)
        packer_confirm_email = self.env.ref('teeni_inventory.email_packer_confirm_template')
        packer_confirm_email.send_mail(self.id)

    def wh_assist_process(self):
        user = self.env.user
        for rec in self:
            rec.wh_process_date = fields.Date.today()
            rec.wh_process_id = user.id
            if not user.has_group('teeni_inventory.group_warehouse_assist_rights'):
                raise Warning(_("Only WH Assist can Process "))
        rec.state = 'processed'
        subject = "Item Processed by" + str(user.partner_id.name)
        body = "Operation " + rec.name + " have been processed by " + str(user.partner_id.name)
        notification = (
                           '<div class="stock.picking"><a href="#" class="o_redirect" data-oe-id="%s"></a></div>') % (
                           rec.name)
        post_vars = {'subject': subject, 'body': notification + body, }
        rec.message_post(type="notification", subtype="mail.mt_comment",
                       needaction_partner_ids=[(user.partner_id.id)], **post_vars)
        wha_processed_email = self.env.ref('teeni_inventory.wh_assist_processed_template')
        wha_processed_email.send_mail(self.id)

    def wha_verify(self):
        group_ids = ['65']
        user_ids = self.env['res.users'].search([('groups_id','in',group_ids)])
        partner_ids = []
        for user_id in user_ids:
            partner_ids += self.env['res.partner'].search([('id','=',user_id.partner_id.id)],limit=1)
        user = self.env.user
        for rec in self:
            rec.receipt_verified_date = fields.Date.today()
            rec.receipt_verified_id = user.id
            if not user.has_group('teeni_inventory.group_warehouse_assist_rights'):
                raise Warning(_("Only WH Assist can Verify Receipt"))
        rec.state = 'verified'
        subject = "Receipt verified by " + str(user.partner_id.name)
        body = "Receipt " + rec.name + " have been verified by " + str(user.partner_id.name)
        notification = (
                           '<div class="stock.picking"><a href="#" class="o_redirect" data-oe-id="%s"></a></div>') % (
                           rec.name)
        post_vars = {'subject': subject, 'body': notification + body, }
        rec.message_post(type="notification", subtype="mail.mt_comment",
                       needaction_partner_ids=[(partner_ids)], **post_vars)
        wha_verify_email = self.env.ref('teeni_inventory.wh_assist_verify_template')
        wha_verify_email.send_mail(self.id)

    def deliver_confirm(self):
        user = self.env.user
        for rec in self:
            if not user.id == rec.assigned_driver_id.id:
                raise Warning(_("Only assigned driver can deliver"))
            rec.deliver_confirm_date = fields.Date.today()
            rec.state = "delivery_d"

    def store_reject(self):
        user = self.env.user
        group_ids = ['69']
        user_ids = self.env['res.users'].search([('groups_id','in',group_ids)])
        partner_ids = []
        for user_id in user_ids:
            partner_ids += self.env['res.partner'].search([('id','=',user_id.partner_id.id)],limit=1)
        for rec in self:
            if not user.id == rec.assigned_driver_id.id:
                raise Warning(_("Only assigned driver can submit store reject"))
            subject = "DO " + str(rec.name) + " have been Rejected"
            body = "DO " + rec.name + " have been marked as Store Reject by " + str(rec.assigned_driver_id.name)
            notification = (
                               '<div class="stock.picking"><a href="#" class="o_redirect" data-oe-id="%s"></a></div>') % (
                               rec.name)
            post_vars = {'subject': subject, 'body': notification + body, }
            rec.message_post(type="notification", subtype="mail.mt_comment",
                       needaction_partner_ids=partner_ids, **post_vars)
            rec.state = 's_rejected'

    def fail_deliver(self):
        user = self.env.user
        group_ids = ['69']
        user_ids = self.env['res.users'].search([('groups_id','in',group_ids)])
        partner_ids = []
        for user_id in user_ids:
            partner_ids += self.env['res.partner'].search([('id','=',user_id.partner_id.id)],limit=1)
        for rec in self:
            if not user.id == rec.assigned_driver_id.id:
                raise Warning(_("Only assigned driver can submit fail_deliver"))
            subject = "DO " + str(rec.name) + " is Fail to Deliver"
            body = "DO " + rec.name + " have been marked as Fail To Deliver by " + str(rec.assigned_driver_id.name)
            notification = (
                               '<div class="stock.picking"><a href="#" class="o_redirect" data-oe-id="%s"></a></div>') % (
                               rec.name)
            post_vars = {'subject': subject, 'body': notification + body, }
            rec.message_post(type="notification", subtype="mail.mt_comment",
                       needaction_partner_ids=partner_ids, **post_vars)
            rec.assigned_delivery_date = ''
            rec.state = 'f_delivery'

    @api.multi
    @api.depends('state', 'is_locked')
    def _compute_show_validate(self):
        for picking in self:
            if not (picking.immediate_transfer) and picking.state == 'draft':
                picking.show_validate = False
            elif picking.state not in ('draft', 'waiting', 'confirmed', 'assigned', 'approved', 'submitted',
                                       'verified') or not picking.is_locked:
                picking.show_validate = False
            else:
                picking.show_validate = True

    # IN PICK: WH ASSIST VERIFY => DONE
    @api.multi
    def button_validate(self):
        user = self.env.user
        self.ensure_one()
        if not self.move_lines and not self.move_line_ids:
            raise UserError(_('Please add some items to move.'))
        for rec in self:
            if rec.picking_type_name == 'Pick' and not user.has_group('teeni_inventory.group_can_process_picking'):
                if user.id not in self.packer_id.ids:
                    raise Warning(_("Only assigned packers can perform picking"))
            if rec.picking_type_name == 'Receipts':
                rec.wh_process_date = fields.Date.today()
                rec.wh_process_id = user.id
        # If no lots when needed, raise error
        picking_type = self.picking_type_id
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
                                 self.move_line_ids.filtered(lambda m: m.state not in ('done','cancel') or m.picking_id.is_out_for_delivery==True))
        no_reserved_quantities = all(
            float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in
            self.move_line_ids)
        if no_reserved_quantities and no_quantities_done:
            raise UserError(_(
                'You cannot validate a transfer if no quantites are reserved nor done. To force the transfer, switch in edit more and encode the done quantities.'))

        if picking_type.use_create_lots or picking_type.use_existing_lots:
            lines_to_check = self.move_line_ids
            if not no_quantities_done:
                lines_to_check = lines_to_check.filtered(
                    lambda line: float_compare(line.qty_done, 0,
                                               precision_rounding=line.product_uom_id.rounding)
                )

            for line in lines_to_check:
                product = line.product_id
                if product and product.tracking != 'none':
                    if not line.lot_name and not line.lot_id:
                        raise UserError(
                            _('You need to supply a Lot/Serial number for product %s.') % product.display_name)

        lines = self.move_line_ids
        message = ""
        for line in lines:
            no_reserved_quantities = float_is_zero(line.product_qty, precision_rounding=line.product_uom_id.rounding)
            if no_reserved_quantities:
                message = message + _('You have not resered %s for this move') % \
                          (line.product_id.name)
                # # We check if some products are available in other warehouses.
                precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                # _logger.debug("FUCKING COMPAE %s",float_compare(product.virtual_available, line.product_id.virtual_available, precision_digits=precision))
                if float_compare(product.virtual_available, line.product_id.virtual_available, precision_digits=precision) == -1:
                    message += _('\nThere are %s %s available across all warehouses:\n') % \
                            (line.product_id.virtual_available, product.uom_id.name)
                    for warehouse in self.env['stock.warehouse'].search([]):
                        quantity = line.product_id.with_context(warehouse=warehouse.id).virtual_available
                        if quantity > 0:
                            message += "- %s: %s %s\n\n" % (warehouse.name, quantity, line.product_id.uom_id.name)

        if no_quantities_done and self.picking_type_name == 'Receipts':
            view = self.env.ref('teeni_inventory.teeni_view_immediate_transfer')
            wiz = self.env['teeni.stock.immediate.transfer'].create({'teeni_pick_ids': [(4, self.id)]})
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'teeni.stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }
        elif self.picking_type_name != 'Receipts' and no_quantities_done:
            raise Warning(_("Please record done quantities"))

        if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
            view = self.env.ref('stock.view_overprocessed_transfer')
            wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.overprocessed.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        # Check backorder should check for other barcodes
        if self._check_backorder() and self.picking_type_name != 'Delivery Orders':
            mv = self.env['stock.move'].sudo().search([('origin', '=', self.origin), ('state', '=', 'waiting')])
            print("MLI", self.product_id.id, self.id)
            for rec in mv:
                cur_mv = self.env['stock.move'].sudo().search(
                    [('origin', '=', self.origin), ('picking_id', '=', self.id),
                     ('product_id', '=', rec.product_id.id)])
                if not cur_mv:
                    rec.mapped('move_line_ids').unlink()
                    rec.unlink()
                else:
                    rec.reserved_availability = cur_mv.reserved_availability
                    rec.quantity_done = cur_mv.quantity_done

            return self.teeni_action_generate_backorder_wizard()
        if self.picking_type_name == 'Delivery Orders':
            subject = "DO verified by " + str(user.partner_id.name)
            body = "DO " + rec.name + " have been verified by " + str(user.partner_id.name)
            notification = (
                           '<div class="stock.picking"><a href="#" class="o_redirect" data-oe-id="%s"></a></div>') % (
                           rec.name)
            post_vars = {'subject': subject, 'body': notification + body, }
            rec.message_post(type="notification", subtype="mail.mt_comment",
                       needaction_partner_ids=[(user.partner_id.id)], **post_vars)
            log_verify_email = self.env.ref('teeni_inventory.log_assist_verify_template')
            log_verify_email.send_mail(self.id)
            return self.driver_assign()
        elif self.picking_type_name == 'Internal Transfers':
            self.wh_assist_process()
        else:
            mv = self.env['stock.move'].sudo().search([('origin', '=', self.origin), ('state', '=', 'waiting')])
            print("MLI", self.product_id.id, self.id)
            for rec in mv:
                cur_mv = self.env['stock.move'].sudo().search([('origin', '=', self.origin), ('picking_id', '=', self.id), ('product_id', '=', rec.product_id.id)])
                if not cur_mv:
                    rec.mapped('move_line_ids').unlink()
                    rec.unlink()
            self.action_done()
        return

    @api.multi
    def _create_backorder(self, backorder_moves=[]):
        """ Move all non-done lines into a new backorder picking.
        """
        backorders = self.env['stock.picking']
        for picking in self:
            if self.picking_type_name != 'Delivery Orders':
                moves_to_backorder = picking.move_lines.filtered(lambda x: x.state not in ('done', 'cancel'))
                if moves_to_backorder:
                    backorder_picking = picking.copy({
                        'name': '/',
                        'move_lines': [],
                        'move_line_ids': [],
                        'backorder_id': picking.id
                    })
                    picking.message_post(
                        body=_('The backorder <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created.') % (
                            backorder_picking.id, backorder_picking.name))
                    moves_to_backorder.write({'picking_id': backorder_picking.id})
                    moves_to_backorder.mapped('package_level_id').write({'picking_id':backorder_picking.id})
                    moves_to_backorder.mapped('move_line_ids').write({'picking_id': backorder_picking.id})
                    backorder_picking.action_assign()
                    backorders |= backorder_picking
        return backorders

    def action_reject(self):
        user = self.env.user
        for rec in self:
            rec.reject_date = fields.Date.today()
            rec.reject_id = user.id
            if not user.has_group('teeni_inventory.group_operation_manager_rights'):
                raise Warning(_("Only Manager can reject request"))
            rec.state = 'rejected'

    def check_po_expire(self):
        group_ids = ['66','67','69']
        user_ids = self.env['res.users'].search([('groups_id','in',group_ids)])
        partner_ids = []
        for user_id in user_ids:
            partner_ids += self.env['res.partner'].search([('id','=',user_id.partner_id.id)],limit=1)
        match = self.search([])
        for i in match:
            customer = self.env['res.partner'].search([('id','=','partner_id')],limit=1)
            if customer.parent_id:
                customer = customer.parent_id
            if customer.po_term_id:
                po_terms = customer.po_term_id.days
                date_order = i.sale_id.date_order.date()
                if i.picking_type_name =="Delivery Orders" and i.state == "done":
                    if fields.Date.today() > date_order + timedelta(days=po_terms):
                        i.action_cancel()
                        subject = i.name + " have Exceeded The PO terms"
                        body = i.name + " have Exceeded The PO terms"
                        notification = (
                                           '<div class="stock.picking"><a href="#" class="o_redirect" data-oe-id="%s">#%s</a></div>') % (
                                           i.id, i.name,)
                        post_vars = {'subject': subject, 'body': notification + body, }
                        i.message_post(type="notification", subtype="mail.mt_comment",
                                                  needaction_partner_ids=partner_ids, **post_vars)

    def teeni_action_generate_backorder_wizard(self):
        view = self.env.ref('teeni_inventory.teeni_view_backorder_confirmation')
        wiz = self.env['teeni.stock.backorder.confirmation'].create({'teeni_pick_ids': [(4, p.id) for p in self]})
        return {
            'name': _('Create Backorder?'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teeni.stock.backorder.confirmation',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
            'context': self.env.context,
        }

    def driver_assign(self):
        view = self.env.ref('teeni_inventory.assign_driver_view')
        wiz = self.env['assign.driver.wiz'].create({'teeni_pick_ids': [(4, p.id) for p in self]})
        if self.assigned_driver_id:
            wiz.driver_id = self.assigned_driver_id.id
            wiz.delivery_date = self.assigned_delivery_date
            # _logger.debug("FUCKING WIZ", wiz.driver_id.id, wiz.delivery_date)
            subject = self.name + " assgined to you"
            body = "a Delivery Number "+ self.name + " have been assigned to you, please check the mobile app"
            notification = (
                               '<div class="stock.picking"><a href="#" class="o_redirect" data-oe-id="%s"></a></div>') % (
                               self.name)
            post_vars = {'subject': subject, 'body': notification + body, }
            self.message_post(type="notification", subtype="mail.mt_comment",
                       needaction_partner_ids=[(4, self.assigned_driver_id.partner_id.id)], **post_vars)
            wiz.process()
        return {
            'name': _('Assign Driver?'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'assign.driver.wiz',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
            'context': self.env.context,
        }

    @api.multi
    def action_cancel(self):
        self.mapped('move_lines')._action_cancel()
        self.write({'is_locked': True})
        do = self.env['stock.picking'].search(
            [('sale_id', '=', self.sale_id.id), ('id', '!=', self.id), ('state', '!=', 'cancel')])

        for rec in do:
            if self.id != False and self.sale_id:
                query = "update stock_picking set state='cancel' where id='" + str(rec.id) + "'"
                self._cr.execute(query)
        return True

    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
        result = super(StockPicking, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                        submenu=submenu)
        print(view_type, "Res", result)
        if view_type == 'tree':
            user = self.env.user
            picking = self.env['stock.picking'].sudo().search([])

            pickright = False
            if (user.has_group('teeni_inventory.group_packer_rights')
                and user.has_group('teeni_inventory.group_warehouse_assist_rights')
                and user.has_group('teeni_inventory.group_logistic_assist_rights')
                and user.has_group('stock.group_stock_manager')):
                pickright = True

            true_id = []
            false_id = []

            if pickright or user.has_group('teeni_inventory.group_can_process_picking'):
                query = "update stock_picking set can_view='True' where (can_view='False' or can_view is null)"
                self._cr.execute(query)
            else:
                for rec in picking:
                   if rec.picking_type_name == "Pick" and self.env.uid not in rec.packer_id.ids:
                       false_id.append(rec.id)
                       # rec.sudo().write({"can_view": False})
                   else:
                       true_id.append(rec.id)
                        # rec.sudo().write({"can_view": True})
                query = "update stock_picking set can_view='True' where id in "+str(tuple(true_id))
                self._cr.execute(query)
                query = "update stock_picking set can_view='False' where id in " + str(tuple(false_id))
                self._cr.execute(query)

        return result


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.onchange('product_id')
    def domain_lot(self):
        list_lot = []
        lot = self.env['stock.production.lot'].search([('product_id', '=', self.product_id.id)])
        for rec in lot:
            if rec.product_qty > 0:
                list_lot.append(rec.id)
        print("LOT", list_lot, "PID", self.product_id.id)
        return {'domain': {'lot_id': [('id', 'in', list_lot)]}}

    teeni_remarks = fields.Char("Remarks", related='move_id.teeni_remarks')

    ml_available_qty = fields.Float(string="Available Qty", store=True, readonly=True)
    rec_lot_number = fields.Many2many('stock.production.lot', string="Rec Lot Number", related='move_id.rec_lot_number')
    rec_lot_number_name = fields.Char(compute="compute_lot_no")

    @api.onchange('product_id')
    def onchange_product_id(self):
        total_avail = self.env['stock.quant']._get_available_quantity(self.product_id,
                                                                      self.location_id) if self.product_id else 0.0
        self.ml_available_qty = total_avail

    def compute_lot_no(self):
        for rec in self:
            lot_no_name = ""
            for lot in rec.rec_lot_number:
                lot_no_name += lot.name + ","
            if lot_no_name:
                lot_no_name = lot_no_name[:-1]
            rec.rec_lot_number_name = lot_no_name

    @api.onchange('qty_done')
    def onchange_qty_done(self):
        for rec in self:
            if rec.qty_done > rec.product_uom_qty:
                raise Warning(_("Can't set more than reserved quantity"))

    api.onchange('qty_done')
    api.depends('qty_done')
    def onchange_done(self):
        for rec in self:
            if (rec.picking_id.state not in ['approved', 'processed', 'verified']) and rec.qty_done != 0:
                raise Warning(_("Cannot Process when not approved"))

    def _action_done(self):
        """ This method is called during a move's `action_done`. It'll actually move a quant from
                the source location to the destination location, and unreserve if needed in the source
                location.

                This method is intended to be called on all the move lines of a move. This method is not
                intended to be called when editing a `done` move (that's what the override of `write` here
                is done.
                """
        Quant = self.env['stock.quant']

        # First, we loop over all the move lines to do a preliminary check: `qty_done` should not
        # be negative and, according to the presence of a picking type or a linked inventory
        # adjustment, enforce some rules on the `lot_id` field. If `qty_done` is null, we unlink
        # the line. It is mandatory in order to free the reservation and correctly apply
        # `action_done` on the next move lines.
        ml_to_delete = self.env['stock.move.line']
        for ml in self:
            # Check here if `ml.qty_done` respects the rounding of `ml.product_uom_id`.
            uom_qty = float_round(ml.qty_done, precision_rounding=ml.product_uom_id.rounding, rounding_method='HALF-UP')
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            qty_done = float_round(ml.qty_done, precision_digits=precision_digits, rounding_method='HALF-UP')
            if float_compare(uom_qty, qty_done, precision_digits=precision_digits) != 0:
                raise UserError(_('The quantity done for the product "%s" doesn\'t respect the rounding precision \
                                          defined on the unit of measure "%s". Please change the quantity done or the \
                                          rounding precision of your unit of measure.') % (
                ml.product_id.display_name, ml.product_uom_id.name))

            qty_done_float_compared = float_compare(ml.qty_done, 0, precision_rounding=ml.product_uom_id.rounding)
            if qty_done_float_compared > 0:
                if ml.product_id.tracking != 'none':
                    picking_type_id = ml.move_id.picking_type_id
                    if picking_type_id:
                        if picking_type_id.use_create_lots:
                            # If a picking type is linked, we may have to create a production lot on
                            # the fly before assigning it to the move line if the user checked both
                            # `use_create_lots` and `use_existing_lots`.
                            if ml.lot_name and not ml.lot_id:
                                lot = self.env['stock.production.lot'].create(
                                    {'name': ml.lot_name, 'product_id': ml.product_id.id}
                                )
                                ml.write({'lot_id': lot.id})
                        elif not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots:
                            # If the user disabled both `use_create_lots` and `use_existing_lots`
                            # checkboxes on the picking type, he's allowed to enter tracked
                            # products without a `lot_id`.
                            continue
                    elif ml.move_id.inventory_id:
                        # If an inventory adjustment is linked, the user is allowed to enter
                        # tracked products without a `lot_id`.
                        continue

                    if not ml.lot_id:
                        raise UserError(
                            _('You need to supply a Lot/Serial number for product %s.') % ml.product_id.display_name)
            elif qty_done_float_compared < 0:
                raise UserError(_('No negative quantities allowed'))
            else:
                ml_to_delete |= ml
        ml_to_delete.unlink()

        # Now, we can actually move the quant.
        done_ml = self.env['stock.move.line']
        for ml in self - ml_to_delete:
            if ml.product_id.type == 'product':
                rounding = ml.product_uom_id.rounding

                # if this move line is force assigned, unreserve elsewhere if needed
                if not ml.location_id.should_bypass_reservation() and float_compare(ml.qty_done, ml.product_uom_qty,
                                                                                    precision_rounding=rounding) > 0:
                    qty_done_product_uom = ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id,
                                                                               rounding_method='HALF-UP')
                    extra_qty = qty_done_product_uom - ml.product_qty
                    ml._free_reservation(ml.product_id, ml.location_id, extra_qty, lot_id=ml.lot_id,
                                         package_id=ml.package_id, owner_id=ml.owner_id, ml_to_ignore=done_ml)
                # unreserve what's been reserved
                if not ml.location_id.should_bypass_reservation() and ml.product_id.type == 'product' and ml.product_qty:
                    try:
                        Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty,
                                                        lot_id=ml.lot_id, package_id=ml.package_id,
                                                        owner_id=ml.owner_id, strict=True)
                    except UserError:
                        Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=False,
                                                        package_id=ml.package_id, owner_id=ml.owner_id, strict=True)

                # move what's been actually done
                quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id,
                                                               rounding_method='HALF-UP')
                available_qty, in_date = Quant._update_available_quantity(ml.product_id, ml.location_id, -quantity,
                                                                          lot_id=ml.lot_id, package_id=ml.package_id,
                                                                          owner_id=ml.owner_id)
                if available_qty < 0 and ml.lot_id:
                    # see if we can compensate the negative quants with some untracked quants
                    untracked_qty = Quant._get_available_quantity(ml.product_id, ml.location_id, lot_id=False,
                                                                  package_id=ml.package_id, owner_id=ml.owner_id,
                                                                  strict=True)
                    if untracked_qty:
                        taken_from_untracked_qty = min(untracked_qty, abs(quantity))
                        Quant._update_available_quantity(ml.product_id, ml.location_id, -taken_from_untracked_qty,
                                                         lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id)
                        Quant._update_available_quantity(ml.product_id, ml.location_id, taken_from_untracked_qty,
                                                         lot_id=ml.lot_id, package_id=ml.package_id,
                                                         owner_id=ml.owner_id)
                Quant._update_available_quantity(ml.product_id, ml.location_dest_id, quantity, lot_id=ml.lot_id,
                                                 package_id=ml.result_package_id, owner_id=ml.owner_id, in_date=in_date)
            done_ml |= ml
        # Reset the reserved quantity as we just moved it to the destination location.
        (self - ml_to_delete).with_context(bypass_reservation_update=True).write({
            'product_uom_qty': 0.00,
            'date': fields.Datetime.now(),
        })
        for ml in self:
            if ml.picking_id.picking_type_id.code == 'incoming':
                pol = self.env['purchase.order.line'].search([('id','=',ml.move_id.purchase_line_id.id)])
                for rec in pol:
                   lot = self.env['stock.production.lot'].search([('id', '=', ml.lot_id.id)])
                   lot.sudo().write({'cost': rec.price_unit})

        for row in self:
            if row.picking_id.picking_type_id.code in ['incoming', 'internal']:
                get_all_pick = self.env['stock.picking'].sudo().search([('state', '=', 'confirmed'), ('picking_type_id.name', '=', 'Pick')])
                for allrec in get_all_pick:
                    allrec.action_assign()

class StockQuant(models.Model):
    _inherit = "stock.quant"

    def low_stock_reminder(self):
        group_ids = ['66','67','69']
        user_ids = self.env['res.users'].search([('groups_id','in',group_ids)])
        partner_ids = []
        for user_id in user_ids:
            partner_ids += self.env['res.partner'].search([('id','=',user_id.partner_id.id)],limit=1)
        match = self.search([])
        for i in match:
            product_type = self.env['product.template'].search([('id', '=', i.product_id.id)], limit=1).type
            if product_type == 'product' and i.quantity <= 100:
                product_name = self.env['product.template'].search([('id', '=', i.product_id.id)], limit=1)
                subject = product_name.name + " quantity is less than 100."
                body = product_name.name + " quantity is less than 100."
                notification = (
                                   '<div class="product.template"><a href="#" class="o_redirect" data-oe-id="%s">#%s</a></div>') % (
                                   product_name.id, product_name.name,)
                post_vars = {'subject': subject, 'body': notification + body, }
                product_name.message_post(type="notification", subtype="mail.mt_comment",
                                          needaction_partner_ids=partner_ids, **post_vars)


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    # life_date = fields.Datetime(string='End of Life Date',
    #     help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.')
    use_date = fields.Datetime(string='Best before Date',
                               help='This is the date on which the goods with this Serial Number start deteriorating, without being dangerous yet.',
                               required=True)
    # removal_date = fields.Datetime(string='Removal Date',
    #     help='This is the date on which the goods with this Serial Number should be removed from the stock.')
    # alert_date = fields.Datetime(string='Alert Date',
    #     help='Date to determine the expired lots and serial numbers using the filter "Expiration Alerts".')
    # product_expiry_alert = fields.Boolean(compute='_compute_product_expiry_alert', help="The Alert Date has been reached.")

    exp_code = fields.Many2one('teeni.exp.code',string="Expiry Code")

    cost = fields.Float()

    @api.onchange('exp_code')
    def _exp_duration(self):
        temp_date = fields.Datetime.now()
        if self.use_date:
            temp_date = self.use_date
            self.use_date = temp_date + relativedelta(years=self.exp_code.exp_year)

    def removal_reminder(self):
        match = self.search([])
        date_now = fields.Datetime.now()
        group_ids = ['66','67','69']
        user_ids = self.env['res.users'].search([('groups_id','in',group_ids)])
        partner_ids = []
        for user_id in user_ids:
            partner_ids += self.env['res.partner'].search([('id','=',user_id.partner_id.id)],limit=1)
        for i in match:
            if i.removal_date:
                if i.removal_date - date_now <= timedelta(days=5):
                    subject = "Lot number " + i.name + " need to be remove soon"
                    body = i.product_id.name + " of lot number " + i.name + " need to be remove on " + str(
                        i.removal_date)
                    notification = (
                                       '<div class="stock.production.lot"><a href="#" class="o_redirect" data-oe-id="%s"></a></div>') % (
                                       i.name)
                    post_vars = {'subject': subject, 'body': notification + body, }
                    i.message_post(type="notification", subtype="mail.mt_comment",
                                   needaction_partner_ids=partner_ids, **post_vars)


class ExpCode(models.Model):
    _name = 'teeni.exp.code'

    name = fields.Char(string="Expiry Code")
    exp_year = fields.Integer('Expiry Years')


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'pull' or 'pull_push') set on it.

        :param procurement: browse record
        :rtype: dictionary
        '''
        date_expected = fields.Datetime.to_string(
            fields.Datetime.from_string(values['date_planned']) - relativedelta(days=self.delay or 0)
        )
        # it is possible that we've already got some move done, so check for the done qty and create
        # a new move with the correct qty
        qty_left = product_qty
        move_values = {
            'name': name[:2000],
            'company_id': self.company_id.id or self.location_src_id.company_id.id or self.location_id.company_id.id or
                          values['company_id'].id,
            'product_id': product_id.id,
            'product_uom': product_uom.id,
            'product_uom_qty': qty_left,
            'partner_id': self.partner_address_id.id or (
                values.get('group_id', False) and values['group_id'].partner_id.id) or False,
            'location_id': self.location_src_id.id,
            'location_dest_id': location_id.id,
            'move_dest_ids': values.get('move_dest_ids', False) and [(4, x.id) for x in values['move_dest_ids']] or [],
            'rule_id': self.id,
            'procure_method': self.procure_method,
            'origin': origin,
            'picking_type_id': self.picking_type_id.id,
            'group_id': group_id,
            'route_ids': [(4, route.id) for route in values.get('route_ids', [])],
            'warehouse_id': self.propagate_warehouse_id.id or self.warehouse_id.id,
            'date': date_expected,
            'date_expected': date_expected,
            'propagate': self.propagate,
            'priority': values.get('priority', "1"),
            'available_qty': product_id.qty_available
        }
        for field in self._get_custom_move_fields():
            if field in values:
                move_values[field] = values.get(field)
        return move_values
