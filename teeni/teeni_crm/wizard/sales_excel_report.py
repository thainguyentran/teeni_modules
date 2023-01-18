import base64
import io

from odoo import api, fields, models, _
from datetime import datetime
import pytz


class SalesReportExcel(models.AbstractModel):
    _name = 'report.teeni_crm.sr_excel'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, partners):
        for obj in partners:
            #print(data,obj.name,partners)
            obj.model = self.env.context.get('active_model')
            docs = self.env[obj.model].browse(self.env.context.get('active_id'))

            # date_from = docs.year
            # date_to  = docs.month
            comp = self.env.user.company_id.name
            sheet_name = "SR"
            sheet = workbook.add_worksheet(sheet_name)
            format4 = workbook.add_format({'font_size': 16, 'align': 'center', 'bold': True, 'text_wrap': True})
            formate5 = workbook.add_format({'font_size': 12, 'align': 'left'})
            formate6 = workbook.add_format()
            formate7 = workbook.add_format()
            formate8 = workbook.add_format({'font_size': 12, 'align': 'center', 'valign': 'vcenter', 'bold': True })
            formate8.set_border(1)
            # sheet.freeze_panes(9, 7)
            # formate8.set_bg_color('cyan')
            formate7.set_font_name('Quantity')
            formate6.set_border(1)
            formate5.set_bg_color('blue')
            formate5.set_font_color('white')
            formate5.set_border(1)
            sheet.merge_range('A1:O1', 'SALES REPORT', format4)

            # image_width = 190.0
            # image_height = 182.0
            #
            # cell_width = 64.0
            # cell_height = 50.0
            #
            # x_scale = cell_width / image_width
            # y_scale = cell_height / image_height
            # buf_image = io.BytesIO(base64.b64decode(self.env.user.company_id.logo))
            # sheet.insert_image('K2:M2', "", {'image_data': buf_image, 'x_scale': x_scale, 'y_scale': y_scale})
            sheet.set_column('A3:A3', 12)
            sheet.write('A3', "Sale Order", formate8)
            sheet.set_column('B3:B3', 12)
            sheet.write('B3:B3', "Customer", formate8)
            sheet.set_column('C3:C3', 15)
            sheet.write('C3', "Item Name", formate8)
            sheet.set_column('D3:D3', 12)
            sheet.write('D3', "Brand", formate8)
            sheet.set_column('E3:E3', 20)
            sheet.write('E3', "Ordered Quantity", formate8)
            sheet.set_column('F3:F3', 18)
            sheet.write('F3:F3', "Delivered Quantity", formate8)
            sheet.set_column('G3:G3', 20)
            sheet.write('G3:G3', "Not Delivered Quantity", formate8)
            sheet.set_column('H3:H3', 15)
            sheet.write('H3:H3', "Unit Price", formate8)
            sheet.set_column('I3:I3', 20)
            sheet.write('I3', "Sale Date", formate8)
            sheet.set_column('J3:J3', 20)
            sheet.write('J3', "Delivered Date", formate8)
            sheet.set_column('K3:K3', 20)
            sheet.write('K3', "Value Loss", formate8)


            row_format = workbook.add_format({'font_size': 9, 'text_wrap': True, 'align': 'center', })
            row_format.set_border(1)
            row = 3
            for line in docs.sales_lines:
                sheet.set_row(row, 34)
                sheet.write(row, 0, line.sale_order, row_format)
                sheet.write(row, 1, line.customer_name, row_format)
                sheet.write(row, 2, line.item_name, row_format)
                sheet.write(row, 3, line.brand, row_format)
                sheet.write(row, 4, line.ordered_qty, row_format)
                sheet.write(row, 5, line.delivered_qty, row_format)
                sheet.write(row, 6, line.not_delivered_qty, row_format)
                sheet.write(row, 7, line.unit_price, row_format)
                sheet.write(row, 8, line.sale_date, row_format)
                sheet.write(row, 9, line.delivered_date, row_format)
                sheet.write(row, 10, line.value_loss, row_format)
                row = row + 1


class SalesSummaryReportExcel(models.AbstractModel):
    _name = 'report.teeni_crm.ssr_excel'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, partners):
        for obj in partners:
            #print(data,obj.name,partners)
            obj.model = self.env.context.get('active_model')
            docs = self.env[obj.model].browse(self.env.context.get('active_id'))

            # date_from = docs.year
            # date_to  = docs.month
            comp = self.env.user.company_id.name
            sheet_name = "SSR"
            sheet = workbook.add_worksheet(sheet_name)
            format4 = workbook.add_format({'font_size': 16, 'align': 'center', 'bold': True, 'text_wrap': True})
            formate5 = workbook.add_format({'font_size': 12, 'align': 'left'})
            formate6 = workbook.add_format()
            formate7 = workbook.add_format()
            formate8 = workbook.add_format({'font_size': 12, 'align': 'center', 'valign': 'vcenter', 'bold': True })
            formate8.set_border(1)
            # sheet.freeze_panes(9, 7)
            # formate8.set_bg_color('cyan')
            formate7.set_font_name('Quantity')
            formate6.set_border(1)
            formate5.set_bg_color('blue')
            formate5.set_font_color('white')
            formate5.set_border(1)
            sheet.merge_range('A1:O1', 'SALES SUMMARY REPORT', format4)

            # image_width = 190.0
            # image_height = 182.0
            #
            # cell_width = 64.0
            # cell_height = 50.0
            #
            # x_scale = cell_width / image_width
            # y_scale = cell_height / image_height
            # buf_image = io.BytesIO(base64.b64decode(self.env.user.company_id.logo))
            # sheet.insert_image('K2:M2', "", {'image_data': buf_image, 'x_scale': x_scale, 'y_scale': y_scale})
            sheet.set_column('A3:A3', 12)
            sheet.write('A3', "Sale Order", formate8)
            sheet.set_column('B3:B3', 12)
            sheet.write('B3:B3', "Customer", formate8)
            sheet.set_column('C3:C3', 20)
            sheet.write('C3', "Ordered Quantity", formate8)
            sheet.set_column('D3:D3', 18)
            sheet.write('D3', "Delivered Quantity", formate8)
            sheet.set_column('E3:E3', 20)
            sheet.write('E3', "Not Delivered Quantity", formate8)
            sheet.set_column('F3:F3', 15)
            sheet.write('F3', "Total", formate8)
            sheet.set_column('G3:G3', 20)
            sheet.write('G3', "Sale Date", formate8)
            sheet.set_column('H3:H3', 20)
            sheet.write('H3', "Delivered Date", formate8)
            sheet.set_column('I3:I3', 20)
            sheet.write('I3', "Value Loss", formate8)


            row_format = workbook.add_format({'font_size': 9, 'text_wrap': True, 'align': 'center', })
            row_format.set_border(1)
            row = 3
            for line in docs.sales_lines:
                sheet.set_row(row, 34)
                sheet.write(row, 0, line.sale_order, row_format)
                sheet.write(row, 1, line.customer_name, row_format)
                sheet.write(row, 2, line.ordered_qty, row_format)
                sheet.write(row, 3, line.delivered_qty, row_format)
                sheet.write(row, 4, line.not_delivered_qty, row_format)
                sheet.write(row, 5, line.total, row_format)
                sheet.write(row, 6, line.sale_date, row_format)
                sheet.write(row, 7, line.delivered_date, row_format)
                row = row + 1
