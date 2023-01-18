from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar

import logging
_logger = logging.getLogger(__name__)

#this is a report to see purchase from which supplier,
#so just need to check the po
class SupSumPurchaseReport(models.TransientModel):
    _name = 'sup.sum.purchase.report.wiz'

    supplier_id = fields.Many2one('res.partner')
    from_date = fields.Date()
    to_date = fields.Date()
    teeni_supplier_id = fields.Char(string="Supplier ID")
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
    area_code = fields.Selection([
        ('S1', 'EXTERNAL - LOCAL'),
        ('S2', 'EXTERNAL - OVERSEAS'),
        ('S3', 'INTERNAL - LOCAL'),
        ('S4', 'INTERNAL - OVERSEAS')
    ], string="Supplier Area Code")

    rec_lines = fields.Many2many('sup.sum.purchase.report.detail')
    grand_total = fields.Float()

    def run_process(self):
        list_rec = []
        return_obj = self.env['sup.sum.purchase.report.detail']
        whr_qry = ''

        if self.supplier_id:
            whr_qry += ''' and rp.id=''' + str(self.supplier_id.id)
        if self.teeni_supplier_id:
            whr_qry += ''' and rp.teeni_supplier_id=''' + str(self.teeni_supplier_id)
        if self.group_code:
            whr_qry += ''' and rp.supplier_group_code=''' + str(self.group_code)
        if self.area_code:
            whr_qry += ''' and rp.supplier_area_code=''' + str(self.area_code)
        if self.from_date:
            whr_qry += ''' and po.date_order>='%s' ''' % self.from_date.strftime('%Y-%m-%d 00:00:00')
        if self.to_date:
            whr_qry += ''' and po.date_order<='%s' ''' % self.to_date.strftime('%Y-%m-%d 23:59:59')

        query = '''
                delete from sup_sum_purchase_report_detail;
                select
                    rp.teeni_supplier_id as supplier_id,
                    rp.name as supplier,
                    po.payment_term_id,
                    rc.name as currency,
                    coalesce(ROUND(sum(po.amount_total)::numeric, 2 ),0) as total_purchase
                from
                    res_partner rp,
                    purchase_order po,
                    res_currency rc
                where
                    po.partner_id= rp.id
                    and po.currency_id = rc.id
                    and po.state in ('purchase','done') ''' + whr_qry + '''
                group by rp.teeni_supplier_id,rp.name,rc.name, po.payment_term_id
                order by rp.teeni_supplier_id desc;'''

        self._cr.execute(query)
        query_res = self._cr.dictfetchall()
        in_out_obj = self.env['sup.sum.purchase.report.detail']
        return_obj = self.env['sup.sum.purchase.report.detail']
        _logger.debug("QUERRY RES %s", query_res)
        list_rec = []
        self.grand_total = 0
        for line in query_res:
            pmt_term = ""
            date = fields.Date.today()
            if self.from_date:
                date = self.from_date
            base_curr = self.env['res.currency'].search([('name', '=', 'SGD')])
            foreign_curr = self.env['res.currency'].search([('name', '=', line['currency'])])
            company = self.env['res.company'].browse(self._context.get('company_id')) or self.env['res.users']._get_company()
            date = fields.Date.today()
            base_total = foreign_curr._convert(line['total_purchase'],base_curr,company,date)
            if line['payment_term_id']:
                pmt_term = self.env['account.payment.term'].search([('id','=', line['payment_term_id'])],limit=1).name
            self.grand_total += base_total
            in_out_obj = self.env['sup.sum.purchase.report.detail'].create({
                'supplier_id': line['supplier_id'],
                'supplier': line['supplier'],
                'payment_term': pmt_term,
                'currency': line['currency'],
                'base_amt': base_total,
                'foreign_amt': line['total_purchase'],
            })
            list_rec.append(in_out_obj.id)
            return_obj += self.env['sup.sum.purchase.report.detail'].browse(in_out_obj.id)
        _logger.debug("GRANT TOTAL %s", self.grand_total)
        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_supplier_sum_purchase_report').report_action(self)


class SupSumReportDetail(models.Model):
    _name = 'sup.sum.purchase.report.detail'

    supplier_id = fields.Char(readonly=True)
    supplier = fields.Char(readonly=True)
    payment_term = fields.Char(readonly=True)
    currency = fields.Char(readonly=True)
    foreign_amt = fields.Float(readonly=True)
    base_amt = fields.Float(readonly=True)
