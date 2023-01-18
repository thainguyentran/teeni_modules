from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar

import logging
_logger = logging.getLogger(__name__)


class DriverReport(models.TransientModel):
    _name = 'driver.report.wiz'

    date = fields.Date(string="Delivery Date", default=fields.Date.today())
    driver = fields.Many2one('res.users', string='Driver')

    driver_lines = fields.Many2many('driver.report.lines', string="Driver Report Lines")

    @api.multi
    def run_process(self):
        whr_claus = ""
        if self.date:
            whr_claus += ''' and sp.assigned_delivery_date='%s' ''' % self.date.strftime('%Y-%m-%d')
        if self.driver:
            whr_claus += ''' and sp.assigned_driver_id=''' + str(self.driver.id)
        query = ''' Delete from driver_report_lines;
                    select
                        sp.id as sp_id,
                        sp.name as do_name,
                        sp.assigned_driver_id as driver_id,
                        sp.assigned_delivery_date as delivery_date,
                        rp.name as customer_name
                    from stock_picking sp, res_partner rp
                    where sp.partner_id = rp.id'''+ whr_claus +'''
                    order by sp.assigned_delivery_date, rp.name
 '''

        _logger.debug("QUERRY %s", query)
        self._cr.execute(query)
        query_res = self._cr.dictfetchall()
        in_out_obj = self.env['driver.report.lines']
        return_obj = self.env['driver.report.lines']
        _logger.debug("QUERRY RES %s", query_res)
        print(query_res)
        list_rec = []

        for line in query_res:
            driver_name = self.env['res.users'].browse(line['driver_id']).name
            cus_po_no = self.env['stock.picking'].browse(line['sp_id']).cus_po_num
            in_out_obj = self.env['driver.report.lines'].create({
                'do_name': line['do_name'],
                'driver_name': driver_name,
                'delivery_date': line['delivery_date'],
                'customer_name': line['customer_name'],
                'cus_po_num': cus_po_no
            })
            list_rec.append(in_out_obj.id)
            return_obj += self.env['driver.report.lines'].browse(in_out_obj.id)

        self.driver_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_inventory.action_driver_report').report_action(self)

    @api.multi
    def export_to_excel(self, data):
        return self.env.ref('teeni_inventory.driver_report_excel').report_action(self, data=data, config=False)

    @api.multi
    def form_close(self):
        return {'type': 'ir.actions.act_window_close'}


class DriverReportLines(models.Model):
    _name = 'driver.report.lines'

    do_name = fields.Char(readonly=True)
    driver_name = fields.Char(readonly=True)
    delivery_date = fields.Char(readonly=True)
    customer_name = fields.Char(readonly=True)
    cus_po_num = fields.Char(readonly=True)
