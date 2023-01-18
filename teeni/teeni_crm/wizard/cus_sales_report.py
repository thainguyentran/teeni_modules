from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar

import logging
_logger = logging.getLogger(__name__)


class CusSalesReport(models.TransientModel):
    _name = 'cus.sales.report.wiz'

    customer_id = fields.Many2one('res.partner', string="Name")
    from_date = fields.Date()
    to_date = fields.Date()
    teeni_customer_id = fields.Char(string="Customer ID")
    group_code = fields.Selection([
        ('TDET', 'TRADE DEPTOR - EXTERNAL'),
        ('TDIC', 'TRADE DEPTOR - INTERNAL'),
        ('NTDE', 'NON TRADE DEPTOR - EXTERNAL'),
        ('NTDI', 'NON TRADE DEPTOR - INTERNAL')
    ], string="Group Code")
    area_code = fields.Selection([
        ('C1', 'EXTERNAL - LOCAL'),
        ('C2', 'EXTERNAL - OVERSEAS'),
        ('C3', 'INTERNAL - LOCAL'),
        ('C4', 'INTERNAL - OVERSEAS')
    ], string="Area Code")

    rec_lines = fields.Many2many('cus.sales.report.detail')
    grand_total = fields.Float()

    def run_process(self):
        list_rec = []
        return_obj = self.env['cus.sales.report.detail']
        whr_qry = ''

        if self.customer_id:
            whr_qry += ''' and rp.id=''' + str(self.customer_id.id)
        if self.teeni_customer_id:
            whr_qry += ''' and rp.teeni_customer_id=''' + str(self.teeni_customer_id)
        if self.group_code:
            whr_qry += ''' and rp.customer_group_code=''' + str(self.group_code)
        if self.area_code:
            whr_qry += ''' and rp.customer_area_code=''' + str(self.area_code)
        if self.from_date:
            whr_qry += ''' and so.date_order>='%s' ''' % self.from_date.strftime('%Y-%m-%d 00:00:00')
        if self.to_date:
            whr_qry += ''' and so.date_order<='%s' ''' % self.to_date.strftime('%Y-%m-%d 23:59:59')

        query = '''
                delete from cus_sales_report_detail;
                select
                    rp.teeni_customer_id as customer_id,
                    rp.name as customer,
                    so.user_id as salesperson_id,
                    so.payment_term_id,
                    c.name as currency,
                    coalesce(ROUND(sum(so.amount_total)::numeric, 2 ),0) as foreign_amt
                from
                    res_partner rp,
                    sale_order so,
                    res_currency c,
                    product_pricelist pp
                where
                    so.partner_id=rp.id
                    and pp.currency_id = c.id
                    and so.state in ('sale','done')
                    and so.pricelist_id = pp.id ''' + whr_qry + '''
                group by rp.teeni_customer_id, rp.name,so.user_id,so.payment_term_id,c.name
                order by rp.teeni_customer_id'''

        self._cr.execute(query)
        query_res = self._cr.dictfetchall()
        in_out_obj = self.env['cus.sales.report.detail']
        return_obj = self.env['cus.sales.report.detail']
        _logger.debug("QUERRY RES %s", query_res)
        list_rec = []
        self.grand_total = 0
        for line in query_res:
            pmt_term = ""
            sales_person = ""
            date = fields.Date.today()
            if self.from_date:
                date = self.from_date
            base_curr = self.env['res.currency'].search([('name', '=', 'SGD')])
            foreign_curr = self.env['res.currency'].search([('name', '=', line['currency'])])
            company = self.env['res.company'].browse(self._context.get('company_id')) or self.env['res.users']._get_company()
            date = fields.Date.today()
            base_total = foreign_curr._convert(line['foreign_amt'],base_curr, company, date)
            self.grand_total += base_total
            if line['payment_term_id']:
                pmt_term = self.env['account.payment.term'].search([('id','=', line['payment_term_id'])],limit=1).name
            if line['salesperson_id']:
                sales_person = self.env['res.users'].search([('id','=', line['salesperson_id'])],limit=1).name
            in_out_obj = self.env['cus.sales.report.detail'].create({
                'customer_id': line['customer_id'],
                'customer': line['customer'],
                'salesperson': sales_person,
                'payment_term': pmt_term,
                'currency': line['currency'],
                'base_amt': base_total,
                'foreign_amt': line['foreign_amt'],
            })
            list_rec.append(in_out_obj.id)
            return_obj += self.env['cus.sales.report.detail'].browse(in_out_obj.id)
        _logger.debug("GRANT TOTAL %s", self.grand_total)
        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_customer_sales_report').report_action(self)


class ReportDetail(models.Model):
    _name = 'cus.sales.report.detail'

    customer_id = fields.Char(readonly=True)
    customer = fields.Char(readonly=True)
    salesperson = fields.Char(readonly=True)
    payment_term = fields.Char(readonly=True)
    currency = fields.Char(readonly=True)
    foreign_amt = fields.Float(readonly=True)
    base_amt = fields.Float(readonly=True)
