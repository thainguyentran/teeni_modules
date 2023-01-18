import base64
import io

from odoo import api, fields, models, _
from datetime import datetime
import pytz


class DriverReportExcel(models.AbstractModel):
    _name = 'report.teeni_crm.dr_excel'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, partners):
        for obj in partners:
            obj.model = self.env.context.get('active_model')
            docs = self.env[obj.model].browse(self.env.context.get('active_id'))

            comp = self.env.user.company_id.name
            sheet_name = "DR"
            sheet = workbook.add_worksheet(sheet_name)
            format4 = workbook.add_format({'font_size': 16, 'align': 'center', 'bold': True, 'text_wrap': True})
            formate5 = workbook.add_format({'font_size': 12, 'align': 'left'})
            formate6 = workbook.add_format()
            formate7 = workbook.add_format()
            formate8 = workbook.add_format({'font_size': 12, 'align': 'center', 'valign': 'vcenter', 'bold': True })
            formate8.set_border(1)
            formate7.set_font_name('Quantity')
            formate6.set_border(1)
            formate5.set_bg_color('blue')
            formate5.set_font_color('white')
            formate5.set_border(1)
            sheet.merge_range('A1:O1', 'DRIVER REPORT', format4)
            sheet.set_column('A3:A3', 12)
            sheet.write('A3', "Delivery Order", formate8)
            sheet.set_column('B3:B3', 12)
            sheet.write('B3:B3', "Driver", formate8)
            sheet.set_column('C3:C3', 15)
            sheet.write('C3', "Delivery Date", formate8)
            sheet.set_column('D3:D3', 12)
            sheet.write('D3', "Customer", formate8)
            sheet.set_column('E3:E3', 12)
            sheet.write('E3', "Customer PO Number", formate8)

            row_format = workbook.add_format({'font_size': 9, 'text_wrap': True, 'align': 'center', })
            row_format.set_border(1)
            row = 5
            for line in docs.driver_lines:
                sheet.set_row(row, 34)
                sheet.write(row, 0, line.do_name, row_format)
                sheet.write(row, 1, line.driver_name, row_format)
                sheet.write(row, 2, line.delivery_date, row_format)
                sheet.write(row, 3, line.customer_name, row_format)
                sheet.write(row, 4, line.cus_po_num, row_format)
                row = row + 1
