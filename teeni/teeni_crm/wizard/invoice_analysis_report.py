from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar


class InvoiceAnalysisReport(models.TransientModel):
    _name = 'invoice.analysis.report.wiz'

    customer_id = fields.Many2one('res.partner')
    from_date = fields.Date(required=1, default=datetime.today().date())
    to_date = fields.Date(required=1, default=datetime.today().date())

    rec_lines = fields.Many2many('invoice.analysis.report.detail')

    def run_process(self):
        list_rec = []
        return_obj = self.env['invoice.analysis.report.detail']

        inv = self.env['account.invoice'].search([('date_invoice','>=', self.from_date),('date_invoice','<=', self.to_date),('type','in',['out_invoice','out_refund'])])
        if self.customer_id:
            inv = self.env['account.invoice'].search(
                [('date_invoice', '>=', self.from_date), ('date_invoice', '<=', self.to_date),
                 ('type', 'in', ['out_invoice', 'out_refund']),('partner_id','=',self.customer_id.id)])
        for rec in inv:
            detail = {
                'invoice_no': rec.number,
                'customer_name': rec.partner_id.name,
                'sp': rec.total_in_base_currency if rec.type == 'out_invoice' else -rec.total_in_base_currency,
                'date': rec.date_invoice,
                'currency':rec.currency_id.name,
                'term': rec.incoterm_id.name,
                'total_amount': rec.amount_total if rec.type == 'out_invoice' else -rec.amount_total,
                'pay_date': rec.move_id.date,
                'paid_amount': rec.move_id.amount
            }
            in_out_obj = self.env['invoice.analysis.report.detail'].create(detail)
            list_rec.append(in_out_obj.id)
            return_obj += self.env['invoice.analysis.report.detail'].browse(in_out_obj.id)
        #
        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_customer_invoice_analysis_report').report_action(self)


class ReportDetail(models.Model):
    _name = 'invoice.analysis.report.detail'

    invoice_no = fields.Char(readonly=True)
    customer_name = fields.Char(readonly=True)
    sp = fields.Float(readonly=True)
    date = fields.Date(readonly=True)
    currency = fields.Char(readonly=True)
    term = fields.Char(readonly=True)
    total_amount = fields.Float(readonly=True)
    pay_date = fields.Date(readonly=True)
    paid_amount = fields.Float(readonly=True)
