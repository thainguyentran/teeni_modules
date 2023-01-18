from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar

import logging
_logger = logging.getLogger(__name__)

#This is a report for payment have been made to the supplier,
#so need to check journal entries as well as vendor bill that have been paid
class SupMonthlyPaymentReport(models.TransientModel):
    _name = 'sup.mo.pay.report.wiz'

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

    rec_lines = fields.Many2many('sup.mo.pay.report.detail')
    grand_total = fields.Float()

    def run_process(self):
        list_rec = []
        return_obj = self.env['sup.mo.pay.report.detail']
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
            whr_qry += ''' and ap.payment_date>='%s' ''' % self.from_date.strftime('%Y-%m-%d 00:00:00')
        if self.to_date:
            whr_qry += ''' and ap.payment_date<='%s' ''' % self.to_date.strftime('%Y-%m-%d 23:59:59')

        query = '''
                delete from sup_mo_pay_report_detail;
                select
                    rp.id as s_id,
                    rp.teeni_supplier_id as supplier_id,
                    rp.name as supplier,
                    rc.name as currency,
                    coalesce(ROUND(sum(ap.amount)::numeric, 2 ),0) as foreign_amt,
                    ap.payment_date as pmt_date
                from
                    account_payment ap,
                    res_partner rp,
                    res_currency rc
                where
                    partner_type = 'supplier' and
                    rp.id = ap.partner_id and
                    rc.id = ap.currency_id ''' + whr_qry + '''
                group by rp.id,rc.name,ap.payment_date
                order by rp.teeni_supplier_id asc'''

        self._cr.execute(query)
        query_res = self._cr.dictfetchall()
        in_out_obj = self.env['sup.mo.pay.report.detail']
        return_obj = self.env['sup.mo.pay.report.detail']
        _logger.debug("QUERRY RES %s", query_res)
        list_rec = []
        self.grand_total = 0
        for line in query_res:
            pmt_term = ""
            partner = self.env['res.partner'].search([('id','=',line['s_id'])], limit=1)
            if partner.property_supplier_payment_term_id:
                    pmt_term = self.env['account.payment.term'].search([('id','=',partner.property_supplier_payment_term_id.id)],limit=1).name
            base_curr = self.env['res.currency'].search([('name', '=', 'SGD')])
            foreign_curr = self.env['res.currency'].search([('name', '=', line['currency'])])
            company = self.env['res.company'].browse(self._context.get('company_id')) or self.env['res.users']._get_company()
            _logger.debug("FOREIGN AMT %s", line['foreign_amt'])
            base_amt = foreign_curr._convert(line['foreign_amt'],base_curr, company, line['pmt_date'])
            _logger.debug("BASE AMT %s", base_amt)
            self.grand_total += base_amt
            in_out_obj = self.env['sup.mo.pay.report.detail'].create({
                'supplier_id': line['supplier_id'],
                'supplier': line['supplier'],
                'payment_term': pmt_term,
                'currency': line['currency'],
                'base_amt': base_amt,
                'foreign_amt': line['foreign_amt'],
            })
            list_rec.append(in_out_obj.id)
            return_obj += self.env['sup.mo.pay.report.detail'].browse(in_out_obj.id)
        _logger.debug("GRANT TOTAL %s", self.grand_total)
        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_supplier_mo_pay_report').report_action(self)


class ReportDetail(models.Model):
    _name = 'sup.mo.pay.report.detail'

    supplier_id = fields.Char(readonly=True)
    supplier = fields.Char(readonly=True)
    payment_term = fields.Char(readonly=True)
    currency = fields.Char(readonly=True)
    foreign_amt = fields.Float(readonly=True)
    base_amt = fields.Float(readonly=True)
