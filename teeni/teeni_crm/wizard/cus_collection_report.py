from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)


class CusCollectionReport(models.TransientModel):
    _name = 'cus.collection.report.wiz'

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

    rec_lines = fields.Many2many('cus.collection.report.detail')
    grand_total = fields.Float()

    def run_process(self):
        list_rec = []
        return_obj = self.env['cus.collection.report.detail']
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
            whr_qry += ''' and ap.payment_date>='%s' ''' % self.from_date.strftime('%Y-%m-%d 00:00:00')
        if self.to_date:
            whr_qry += ''' and ap.payment_date<='%s' ''' % self.to_date.strftime('%Y-%m-%d 23:59:59')

        query = '''
                delete from cus_collection_report_detail;
                select
                    rp.id as c_id,
                    rp.teeni_customer_id as customer_id,
                    rp.name as customer,
                    rc.name as currency,
                    coalesce(ROUND(sum(ap.amount)::numeric, 2 ),0) as foreign_amt,
                    ap.payment_date as pmt_date
                from
                    account_payment ap,
                    res_partner rp,
                    res_currency rc
                where
                    partner_type = 'customer' and
                    rp.id = ap.partner_id and
                    rc.id = ap.currency_id ''' + whr_qry + '''
                group by rp.id,rc.name,ap.payment_date
                order by rp.teeni_customer_id asc'''

        self._cr.execute(query)
        query_res = self._cr.dictfetchall()
        in_out_obj = self.env['cus.collection.report.detail']
        return_obj = self.env['cus.collection.report.detail']
        _logger.debug("QUERRY RES %s", query_res)
        list_rec = []
        self.grand_total = 0
        for line in query_res:
            pmt_term = ""
            sales_person = ""
            # date = fields.Date.today()
            # if self.from_date:
            #     date = self.from_date
            base_curr = self.env['res.currency'].search([('name', '=', 'SGD')])
            foreign_curr = self.env['res.currency'].search([('name', '=', line['currency'])])
            company = self.env['res.company'].browse(self._context.get('company_id')) or self.env['res.users']._get_company()

            base_total = foreign_curr._convert(line['foreign_amt'], base_curr, company, line['pmt_date'])
            self.grand_total += base_total

            partner = self.env['res.partner'].search([('id','=',line['c_id'])], limit=1)
            if partner.property_payment_term_id:
                pmt_term = self.env['account.payment.term'].search([('id','=', partner.property_payment_term_id.id)],limit=1).name
            # if line['salesperson_id']:
            #     sales_person = self.env['res.users'].search([('id','=', line['salesperson_id'])],limit=1).name
            in_out_obj = self.env['cus.collection.report.detail'].create({
                'customer_id': line['customer_id'],
                'customer': line['customer'],
                'salesperson': sales_person,
                'payment_term': pmt_term,
                'currency': line['currency'],
                'base_amt': base_total,
                'foreign_amt': line['foreign_amt'],
            })
            list_rec.append(in_out_obj.id)
            return_obj += self.env['cus.collection.report.detail'].browse(in_out_obj.id)
        _logger.debug("GRANT TOTAL %s", self.grand_total)
        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_customer_collection_report').report_action(self)


class ReportDetail(models.Model):
    _name = 'cus.collection.report.detail'

    customer_id = fields.Char(readonly=True)
    customer = fields.Char(readonly=True)
    salesperson = fields.Char(readonly=True)
    payment_term = fields.Char(readonly=True)
    currency = fields.Char(readonly=True)
    foreign_amt = fields.Float(readonly=True)
    base_amt = fields.Float(readonly=True)
