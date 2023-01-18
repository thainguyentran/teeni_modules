from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar

import logging
_logger = logging.getLogger(__name__)


class GeneralAccActyReport(models.TransientModel):
    _name = 'gen.acc.act.report.wiz'

    ac_name =fields.Many2one('account.account', string="A/C Name")
    ac_code = fields.Char(string="A/C Code", related='ac_name.code')
    from_date = fields.Date()
    to_date = fields.Date()
    ds_code = fields.Char(string="D/S Code")
    ds_name = fields.Char(string="D/S Name")

    rec_lines = fields.Many2many('gen.acc.act.report.detail')
    grand_total_debit = fields.Float()
    grand_total_credit = fields.Float()
    balances = fields.Float()

    def run_process(self):
        list_rec = []
        return_obj = self.env['gen.acc.act.report.detail']
        whr_qry = ''

        if self.ac_code:
            whr_qry += ''' and aa.code=''' + str(self.ac_code)
        if self.ac_name:
            whr_qry += ''' and aa.name=''' + str(self.ac_name.name)
        # if self.ds_name:
        #     whr_qry += ''' and rp.teeni_customer_id=''' + str(self.ds_name)
        # if self.ds_code:
        #     whr_qry += ''' and rp.customer_group_code=''' + str(self.ds_code)
        if self.from_date:
            whr_qry += ''' and aml.date>='%s' ''' % self.from_date.strftime('%Y-%m-%d 00:00:00')
        if self.to_date:
            whr_qry += ''' and aml.date<='%s' ''' % self.to_date.strftime('%Y-%m-%d 23:59:59')

        query = '''
                select
                    aa.code as ac_code,
                    aa.name as ac_name,
                    aa.currency_id as curr_id,
                    sum(aml.credit) as amt_cr,
                    sum(aml.debit) as amt_de,
                    sum(aml.balance) as balances,
                    aml.date as date,
                    aml.ref as description,
					COALESCE((select balance from account_move_line rml, account_full_Reconcile ar where rml.move_id=ar.exchange_move_id
					 and rml.full_reconcile_id=aml.full_reconcile_id and not aml.invoice_id is null),0) as gain
                from
                    account_account aa,
                    account_move_line aml
                where
                    aml.account_id = aa.id ''' + whr_qry + '''
                group by aa.code,aa.name,aa.currency_id,aml.date,aml.ref,aml.full_reconcile_id,aml.invoice_id
                order by aa.code
                '''

        self._cr.execute(query)
        query_res = self._cr.dictfetchall()
        in_out_obj = self.env['gen.acc.act.report.detail']
        return_obj = self.env['gen.acc.act.report.detail']
        _logger.debug("QUERRY RES %s", query_res)
        list_rec = []
        self.grand_total = 0
        self.grand_total_debit = 0
        self.grand_total_credit = 0
        self.balances = 0
        for line in query_res:
            # base_curr = self.env['res.currency'].search([('name', '=', 'SGD')])
            curr_name = self.env['res.currency'].search([('id', '=', line['curr_id'])],limit=1).name
            # company = self.env['res.company'].browse(self._context.get('company_id')) or self.env['res.users']._get_company()
            # date = fields.Date.today()
            # base_total = foreign_curr._convert(line['total_sale'],base_curr,company,date)
            self.grand_total_debit += line['amt_de']
            self.grand_total_credit += line['amt_cr']
            self.balances +=line['amt_de']
            self.balances -= line['amt_cr']
            in_out_obj = self.env['gen.acc.act.report.detail'].create({
                'ac_code': line['ac_code'],
                'currency': curr_name,
                'ac_name': line['ac_name'],
                'date': line['date'],
                'description': line['description'],
                'debit': line['amt_de'],
                'credit': line['amt_cr'],
                'balances': self.balances,
                'gain': line['gain']
            })
            list_rec.append(in_out_obj.id)
            return_obj += self.env['gen.acc.act.report.detail'].browse(in_out_obj.id)
        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_general_acc_act_report').report_action(self)


class ReportDetail(models.Model):
    _name = 'gen.acc.act.report.detail'

    ac_code = fields.Char(readonly=True)
    currency = fields.Char(readonly=True)
    ac_name = fields.Char(readonly=True)
    date = fields.Char(readonly=True)
    description = fields.Char(readonly=True)
    debit = fields.Float(readonly=True)
    credit = fields.Float(readonly=True)
    balances = fields.Float(readonly=True)
    gain = fields.Float(readonly=True)
