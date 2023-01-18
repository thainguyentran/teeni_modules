from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar

import logging
_logger = logging.getLogger(__name__)


class PurchaseReport(models.TransientModel):
    _name = 'purchase.report.wiz'

    year = fields.Selection([(num, str(num)) for num in range(2018, (datetime.now().year) + 1)], 'Year',
                            default=datetime.now().year,required=True)
    month = fields.Selection([(num, str(num)) for num in range(1, 13)], string="Month", default=datetime.now().month, required=True)
    #day = fields.Selection([(num, str(num)) for num in range(1, numofday)], string="Day", default=datetime.now().day)
    day = fields.Integer(string="Day", default=datetime.now().day)
    supplier = fields.Many2one('res.partner', string='Supplier')
    supplier_id = fields.Char(string="Supplier ID")
    currency = fields.Many2one('res.currency', 'Currency',
    default=lambda self: self.env.user.company_id.currency_id.id)
    group_code = fields.Selection([
        ('TCET', 'TRADE CREDITOR - EXTERNAL'),
        ('TCIC', 'TRADE CREDITOR - INTERNAL'),
        ('NTCE', 'NON TRADE CREDITOR - EXTERNAL'),
        ('NTIC', 'NON TRADE CREDITOR - INTERNAL'),
        ('NCHD', 'NON-TC-HOLDING'),
        ('NCIC', 'NON-TC-INTERCO'),
        ('NCRP', 'NON-TC-RELATED PARTY'),
        ('NCUH', 'NON-TC-ULTIMATE HOLD'),
        ('NONTRADE', 'NON TRADE CREDITOR'),
        ('OTHER', 'OTHER CREDITORS'),
        ('RELATED', 'RELATED COMPANY'),
        ('TCRP', 'TC-RELATED PARTIES')
    ], string="Supplier Group Code")
    product = fields.Many2one('product.template', string="Product")
    purchase_lines = fields.Many2many('purchase.report.lines', string="Purchase Report Lines")

    @api.multi
    def run_process(self):
        whr_claus = ""
        if self.year:
            whr_claus = " and date_part('year',po.date_order)=" + str(self.year)
        if self.month:
            whr_claus += " and date_part('month',po.date_order)=" + str(self.month)
        if self.day:
            whr_claus += " and date_part('day',po.date_order)=" + str(self.day)
        if self.supplier:
            whr_claus += " and rp.id=" + str(self.supplier.id)
        if self.currency:
            whr_claus += " and po.currency_id=" + str(self.currency.id)
        if self.group_code:
            whr_claus += " and rp.supplier_group_code=" + str(self.group_code)
        if self.supplier_id:
            whr_claus += " and rp.teeni_supplier_id=" + str(self.supplier_id)
        if self.product:
            whr_claus += " and pt.id=" + str(self.product.id)
        query = ''' Delete from purchase_report_lines;
                    select
                        po.name as purchase_order,
                        pt.name as item_name,
                        po.date_order as order_date,
                        pol.product_qty as ordered_qty,
                        pol.qty_received as received_qty,
                        pol.price_unit as unit_price,
                        rc.name as currency,
                        sp.wh_process_date as received_date,
                        rp.name as supplier_name,
                        rp.teeni_supplier_id as supplier_id,
                        rp.supplier_group_code as group_code
                    from purchase_order po,
                        res_partner rp,
                        purchase_order_line pol,
                        product_template pt,
                        stock_picking sp,
                        res_currency rc
                    where po.partner_id = rp.id
                        and pol.order_id = po.id
                        and pol.product_id = pt.id
                        and sp.origin = po.name
                        and po.currency_id = rc.id '''+whr_claus+'''
                    order by po.name
 '''

        _logger.debug("QUERRY %s", query)
        self._cr.execute(query)
        query_res = self._cr.dictfetchall()
        in_out_obj = self.env['purchase.report.lines']
        return_obj = self.env['purchase.report.lines']
        _logger.debug("QUERRY RES %s", query_res)
        print(query_res)
        list_rec = []

        for line in query_res:
            in_out_obj = self.env['purchase.report.lines'].create({
                'purchase_order': line['purchase_order'],
                'supplier_name': line['supplier_name'],
                'item_name': line['item_name'],
                'supplier_id': line['supplier_id'],
                'ordered_qty': line['ordered_qty'],
                'received_qty': line['received_qty'],
                'unit_price': line['unit_price'],
                'order_date': line['order_date'],
                'received_date': line['received_date'],
                'currency': line['currency'],
                'group_code': line['group_code']
            })
            list_rec.append(in_out_obj.id)
            return_obj += self.env['purchase.report.lines'].browse(in_out_obj.id)

        self.purchase_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_purchase_report').report_action(self)

    @api.multi
    def export_to_excel(self, data):
        return self.env.ref('teeni_crm.purchase_report_excel').report_action(self, data=data, config=False)

    @api.multi
    def form_close(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.onchange('day')
    def _day_check(self):
        if self.day:
            if self.year and self.month:
                fd, dayrange = calendar.monthrange(int(self.year), int(self.month))
                if self.day not in range(1, dayrange + 1):
                    raise Warning(_("Please input a correct date."))


class PurchaseReportLines(models.Model):
    _name = 'purchase.report.lines'

    purchase_order = fields.Char(readonly=True)
    supplier_name = fields.Char(readonly=True)
    item_name = fields.Char(readonly=True)
    supplier_id = fields.Char(readonly=True)
    ordered_qty = fields.Char(readonly=True)
    received_qty = fields.Char(readonly=True)
    unit_price = fields.Float(readonly=True)
    order_date = fields.Char(readonly=True)
    received_date = fields.Char(readonly=True)
    currency = fields.Char(readonly=True)
    group_code = fields.Char(readonly=True)
    supplier_id = fields.Char(readonly=True)
