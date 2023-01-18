from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar

import logging
_logger = logging.getLogger(__name__)


class SalesSummaryReport(models.TransientModel):
    _name = 'sales.summary.report.wiz'

    year = fields.Selection([(num, str(num)) for num in range(2018, (datetime.now().year) + 1)], 'Year',
                            default=datetime.now().year,required=True)
    month = fields.Selection([(num, str(num)) for num in range(1, 13)], string="Month", default=datetime.now().month, required=True)
    #day = fields.Selection([(num, str(num)) for num in range(1, numofday)], string="Day", default=datetime.now().day)
    day = fields.Integer(string="Day")
    customer = fields.Many2one('res.partner', string='Customer')

    sales_lines = fields.Many2many('sales.summary.report.lines', string="Sales Report Lines")

    @api.multi
    def run_process(self):
        whr_claus = ""
        if self.year:
            whr_claus = " and date_part('year',sp.date_done)=" + str(self.year)
        if self.month:
            whr_claus += " and date_part('month',sp.date_done)=" + str(self.month)
        if self.day:
            whr_claus += " and date_part('day',sp.date_done)=" + str(self.day)
        if self.customer:
            whr_claus += " and rp.id=" + str(self.customer.id)
        query = ''' Delete from sales_report_lines;
                    select
                        so.name as sale_order,
                        so.amount_total as total,
                        so.confirmation_date as sale_date,
                        sum(sol.product_uom_qty) as total_ordered_qty,
                        sum(sol.qty_delivered) as total_delivered_qty,
                        sp.deliver_confirm_date as delivered_date,
                        rp.name as customer_name
                    from sale_order so,
                        res_partner rp,
                        sale_order_line sol,
                        product_template pt,
                        stock_picking sp
                    where so.partner_id = rp.id
                        and sol.order_id = so.id
                        and sol.product_id = pt.id
                        and sp.origin = so.name '''+whr_claus+'''
                    group by so.name, so.amount_total,so.confirmation_date,sp.deliver_confirm_date,rp.name
                    order by so.name
 '''

        self._cr.execute(query)
        query_res = self._cr.dictfetchall()
        in_out_obj = self.env['sales.summary.report.lines']
        return_obj = self.env['sales.summary.report.lines']
        print(query_res)
        list_rec = []

        for line in query_res:
            in_out_obj = self.env['sales.summary.report.lines'].create({
                'sale_order': line['sale_order'],
                'customer_name': line['customer_name'],
                'total': line['total'],

                'total_ordered_qty': line['total_ordered_qty'],
                'total_delivered_qty': line['total_delivered_qty'],
                'total_not_delivered_qty': float(line['total_ordered_qty']) - float(line['total_delivered_qty']),
                'sale_date': line['sale_date'],
                'delivered_date': line['delivered_date'],
            })
            list_rec.append(in_out_obj.id)
            return_obj += self.env['sales.summary.report.lines'].browse(in_out_obj.id)

        self.sales_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_sales_summary_report').report_action(self)

    @api.multi
    def export_to_excel(self, data):
        return self.env.ref('teeni_crm.sales_summary_report_excel').report_action(self, data=data, config=False)

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


class SalesReportLines(models.Model):
    _name = 'sales.summary.report.lines'

    sale_order = fields.Char(readonly=True)
    customer_name = fields.Char(readonly=True)
    total = fields.Char(readonly=True)
    total_ordered_qty = fields.Char(readonly=True)
    total_delivered_qty = fields.Char(readonly=True)
    total_not_delivered_qty = fields.Char(readonly=True)
    sale_date = fields.Char(readonly=True)
    delivered_date = fields.Char(readonly=True)
