from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime, timedelta
import calendar

import logging
_logger = logging.getLogger(__name__)


class SupplierActivitiyReport(models.TransientModel):
    _name = 'sup.acc.act.report.wiz'

    supplier_id = fields.Many2one('res.partner', string="Name")
    from_date = fields.Date()
    to_date = fields.Date()
    # teeni_supplier_id = fields.Char(string="Supplier ID")
    group_code = fields.Selection([
        ('TDET', 'TRADE DEPTOR - EXTERNAL'),
        ('TDIC', 'TRADE DEPTOR - INTERNAL'),
        ('NTDE', 'NON TRADE DEPTOR - EXTERNAL'),
        ('NTDI', 'NON TRADE DEPTOR - INTERNAL')
    ], string="Group Code")

    currency_type = fields.Selection([('single', 'Single Currency'),('dual', 'Dual Currency')], default="single")

    # currency = fields.Many2one('res.currency', 'Currency',
    # default=lambda self: self.env.user.company_id.currency_id.id)

    rec_lines = fields.Many2many('cus.acc.act.report.detail')
    grand_total_debit = fields.Float()
    grand_total_credit = fields.Float()
    balances = fields.Float()
    bfbalance = fields.Float(default=0)
    foreign_balance = fields.Float(default=0)
    invoice_id = fields.Many2one('account.invoice')

    def run_process(self):
        list_rec = []
        return_obj = self.env['cus.acc.act.report.detail']
        whr_qry = ''

        if self.supplier_id:
            whr_qry += ''' and rp.id=''' + str(self.supplier_id.id)
        # if self.teeni_customer_id:
        #     whr_qry += ''' and rp.id=''' + str(self.teeni_supplier_id)
        if self.group_code:
            whr_qry += ''' and rp.customer_group_code=''' + str(self.group_code)
        # if self.currency:
        #     whr_qry += ''' and aml.currency_id=''' + str(self.currency.id)
        if self.from_date:
            whr_qry += ''' and aml.date>='%s' ''' % self.from_date.strftime('%Y-%m-%d 00:00:00')
        if self.to_date:
            whr_qry += ''' and aml.date<='%s' ''' % self.to_date.strftime('%Y-%m-%d 23:59:59')

        default_account = self.env['ir.property'].get('property_account_payable_id', 'res.partner')
        print("DEF", default_account)
        query = '''
                delete from cus_acc_act_report_detail;
                select
                    aml.date as date,
                    aml.credit as amt_cr,
                    aml.debit as amt_de,
                    -aml.balance as balances,
                    aml.ref as description,
                    aml.invoice_id as inv_id,
                    rp.id as customer_id,
                    -aml.amount_currency as amount_currency,
					COALESCE((select -balance from account_move_line rml, account_full_Reconcile ar where rml.move_id=ar.exchange_move_id
					 and rml.full_reconcile_id=aml.full_reconcile_id and not aml.invoice_id is null),0) as gain
                from
                    account_move_line aml,
                    res_partner rp
                where aml.account_id = '''+str(default_account.id)+''' and
                    aml.partner_id = rp.id ''' + whr_qry


        whr_qry2 = ''
        query2 = ''
        query_res2 = ''
        if self.from_date:
            whr_qry2 += ''' and aml.date<'%s' ''' % self.from_date.strftime('%Y-%m-%d 00:00:00')
            if self.supplier_id:
                whr_qry2 += ''' and rp.id=''' + str(self.supplier_id.id)
            query += '''
                    union all
                    select
                        ''' + "'" + str(self.from_date+timedelta(days=-1)) + "'" + ''' as date,
                        0 as amt_cr,
                        0 as amt_de,
                        -sum(aml.balance) as balances,
                        'B/F Balance' as description,
                        0 as inv_id,
                        rp.id as customer_id,
                        -sum(aml.amount_currency) as amount_currency,
                        0 as gain
                    from
                        account_move_line aml,
                        res_partner rp
                    where aml.account_id = '''+str(default_account.id)+''' and
                        aml.partner_id = rp.id ''' + whr_qry2 + '''
                        group by rp.id
                    '''
            # self._cr.execute(query2)
            # query_res2 = self._cr.dictfetchall()
        query += " order by customer_id,date"
        print("qry", query)
        self._cr.execute(query)

        query_res = self._cr.dictfetchall()

        in_out_obj = self.env['cus.acc.act.report.detail']
        return_obj = self.env['cus.acc.act.report.detail']
        _logger.debug("QUERRY RES %s", query_res)
        _logger.debug("QUERRY RES 2 %s", query_res2)
        list_rec = []
        self.grand_total = 0
        self.grand_total_debit = 0
        self.grand_total_credit = 0
        self.balances = 0
        # for rec in query_res2:
        #     print("QR2", query_res2)
        #     self.bfbalance = float(rec['balances'])
        #     self.foreign_balance = float(rec['foreign_amount_balance'])

        for line in query_res:
            # invoice_id = 0
            pmt_term = ""
            sales_person = ""
            customer_name = ""
            if 'inv_id' in line:
                invoice_id = self.env['account.invoice'].search([('id','=',line['inv_id'])],limit=1)
                if invoice_id.payment_term_id:
                    pmt_term = self.env['account.payment.term'].search([('id','=',invoice_id.payment_term_id.id)],limit=1).name
                if invoice_id.user_id:
                    sales_person = self.env['res.users'].search([('id','=',invoice_id.user_id.id)],limit=1).name
            self.grand_total_debit += line['amt_de']
            self.grand_total_credit += line['amt_cr']
            self.balances +=line['amt_de']
            self.balances -= line['amt_cr']
            customer_name = self.env['res.partner'].search([('id','=',line['customer_id'])],limit=1).name
            in_out_obj = self.env['cus.acc.act.report.detail'].create({
                'customer_name': customer_name,
                'date': line['date'],
                'description': line['description'],
                'payment_term': pmt_term,
                'salesperson': sales_person,
                'debit': line['amt_de'],
                'credit': line['amt_cr'],
                'balances': line['balances'],
                'bfbalance': self.bfbalance,
                'foreign_balance': self.foreign_balance,
                'foreign_amt': line['amount_currency'],
                'gain': line['gain']
            })
            list_rec.append(in_out_obj.id)
            return_obj += self.env['cus.acc.act.report.detail'].browse(in_out_obj.id)
        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_supplier_acc_act_report').report_action(self)


# class ReportDetail(models.Model):
#     _name = 'cus.acc.act.report.detail'
#
#     customer_name = fields.Char(readonly=True)
#     date = fields.Char(readonly=True)
#     description = fields.Char(readonly=True)
#     payment_term = fields.Char(readonly=True)
#     salesperson = fields.Char(readonly=True)
#     debit = fields.Float(readonly=True)
#     credit = fields.Float(readonly=True)
#     balances = fields.Float(readonly=True)
#     bfbalance = fields.Float(readonly=True)
#     foreign_balance = fields.Float(readonly=True)
#     foreign_amt = fields.Float(readonly=True)
