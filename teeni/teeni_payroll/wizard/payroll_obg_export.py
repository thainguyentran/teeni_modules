import base64
import tempfile
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta as rv

from odoo import models, fields, api, _


class OBG(models.TransientModel):
    _name = 'payroll.obg.export.wiz'

    date_start = fields.Date('Date Start',
                             default=lambda *a: time.strftime('%Y-%m-01'))
    date_stop = fields.Date('Date End',
                            default=lambda *a: str(datetime.now() +
                                                   rv(months=+1, day=1,
                                                      days=-1))[:10])

    @api.multi
    def download_file(self):
        cr, uid, context = self.env.args
        context = dict(context)
        if context is None:
            context = {}
        payslip = self.env['hr.payslip'].search([('date_from', '>=', self.date_start), ('date_to', '<=', self.date_stop), ('state', '=', 'done')])
        tgz_tmp_filename = tempfile.mktemp('.' + "txt")
        tmp_file = False
        tmp_file = open(tgz_tmp_filename, "w")
        header_record = 'CORP:001 TEENI ENTERPRISE PTE LTD'.ljust(33) + \
                        ' '.ljust(16) + \
                        'INTERBANK GIRO BANK ORDER LIST'.ljust(30) + \
                        ' '.ljust(12) + \
                        'PRR00700-A PAGE:    1'.ljust(21) + \
                        ' '.ljust(3) + "\r\n"
        tmp_file.write(header_record)

        header_record = 'BANK: 7339-501 OCBC Chulia Street'.ljust(34) + \
                        ' '.ljust(14) + \
                        'FOR THE PERIOD ENDING '+self.date_stop.strftime("%d/%m/%Y")+'           '+fields.Datetime.now().strftime("%d/%m/%Y %H:%M:%S").ljust(2).ljust(43) + \
                        ' '.ljust(3) + "\r\n"
        tmp_file.write(header_record)

        header_record = 'A/C NO: 501256333001'.ljust(34) + \
                        ' '.ljust(3) + "\r\n"
        tmp_file.write(header_record)

        header_record = '<---------------------------- RECEIVING ---------------------------->'.ljust(70) + \
                        ' '.ljust(3) + \
                        'AMOUNT'.rjust(8) + \
                        ' '.ljust(1) + \
                        'EMPLOYEE NO'.ljust(19) + \
                        ' '.ljust(3) + "\r\n"
        tmp_file.write(header_record)

        header_record = 'BANK CODE'.ljust(9) + \
                        ' '.ljust(1) + \
                        'BANK DESCRIPTION'.ljust(16) + \
                        ' '.ljust(6) + \
                        'BRANCH DESCRIPTION'.ljust(18) + \
                        ' '.ljust(3) + \
                        'ACCOUNT NO'.ljust(10) + \
                        ' '.ljust(10) + \
                        'CREDITED'.ljust(8) + \
                        ' '.ljust(1) + \
                        'EMPLOYEE/PAYEE NAME'.ljust(19) + \
                        ' '.ljust(10) + "\r\n"
        tmp_file.write(header_record)
        for rec in payslip:
            credited_amt = rec.line_ids.filtered(lambda l: l.code == 'NET').amount
            detail_record = str(rec.employee_id.bank_account_id.bank_id.bic).ljust(9) + \
                            ' '.ljust(1) + \
                            str(rec.employee_id.bank_account_id.bank_id.name).ljust(16) + \
                            ' '.ljust(6) + \
                            str(rec.employee_id.bank_account_id.branch_id).ljust(18) + \
                            ' '.ljust(3) + \
                            str(rec.employee_id.bank_account_id.acc_number).ljust(10) + \
                            ' '.ljust(10) + \
                            str(credited_amt).rjust(8) + \
                            ' '.ljust(1) + \
                            str(rec.employee_id.employee_no).ljust(19) + \
                            ' '.ljust(10) + "\r\n"
            tmp_file.write(detail_record)
            detail_record = ' '.ljust(82) + \
                            rec.employee_id.name.ljust(19) + \
                            ' '.ljust(10) + "\r\n"
            tmp_file.write(detail_record)

        if tmp_file:
            tmp_file.close()
        file = open(tgz_tmp_filename, "rb")
        out = file.read()
        file.close()
        res = base64.b64encode(out)
        file_name = 'Interbank Giro Report.obg'
        module_rec = self.env['binary.obg.text.file.wizard'].create(
            {'name': file_name, 'cpf_txt_file': res})
        return {'name': _('Text File'),
                'res_id': module_rec.id,
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'binary.obg.text.file.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context}


class BinaryCpfTextFileWizard(models.TransientModel):
    _name = 'binary.obg.text.file.wizard'

    name = fields.Char('Name', size=64)
    cpf_txt_file = fields.Binary('Click On Download Link To Download \
        Text File', readonly=True)

    @api.multi
    def action_back(self):
        return {'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'payroll.obg.export.wiz',
                'target': 'new'}
