from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar


class AgingReport(models.TransientModel):
    _name = 'cus.sum.aging.report.wiz'

    customer_id = fields.Many2one('res.partner')
    aging_date = fields.Date()
    currency_type = fields.Selection([('original', 'Original Currency'),('base', 'Base Currency')], default="original")
    rec_lines = fields.Many2many('cus.sum.aging.report.detail')

    def run_process(self):
        list_rec = []
        return_obj = self.env['cus.sum.aging.report.detail']
        filter_val = [('state', '=', 'open'), ('type', 'in', ['out_invoice', 'out_refund'])]
        if self.customer_id:
            filter_val.append(tuple(['partner_id', '=', self.customer_id.id]))
        if self.aging_date:
            filter_val.append(tuple(['date_invoice', '<=', self.aging_date]))

        inv = self.env['account.invoice'].search(filter_val, order="date_invoice desc")
        partner_list = []
        month_list = []
        last_month = ""
        col = 1
        for rec in inv:

            month = rec.date_invoice.strftime("%b")
            year = rec.date_invoice.strftime("%Y")
            month_year = str(month) + "," + str(year)
            if col == 10:
                month_year = month_year + '+'
                last_month = month_year
            month_dic = {
                "month_year": month_year
            }

            if col<=10:
                if not any(d["month_year"] == month_year for d in month_list):
                    col = col + 1
                    month_list.append(month_dic)

        for rec in inv:
            amt_due = rec.residual_signed
            currency = rec.currency_id.name
            if self.currency_type:
                if self.currency_type == "base":
                    cr = rec.currency_id.rate
                    amt_due = rec.residual_signed/cr
                    currency = rec.company_id.currency_id.name
            month = rec.date_invoice.strftime("%b")
            year = rec.date_invoice.strftime("%Y")
            partner_id = rec.partner_id.id
            partner_name = rec.partner_id.name
            month_year = str(month)+","+str(year)
            advance = 0
            # if self.aging_date:
            #     advance = rec.partner_id.get_previous_balance(self.aging_date)

            print("Adv Amt", advance)
            dic = {
                "partner_id": partner_id,
                "partner_name": partner_name,
                "currency": currency,
                "advance": rec.partner_id.debit-rec.partner_id.credit,
             #   "month_year": str(month)+","+str(year)
            }
            # and d['month'] == month and d['year'] == year
            for v in month_list:
                dic[v["month_year"]] = 0
            if not any(d['partner_id'] == partner_id for d in partner_list):
                dic[month_year] = 0
                partner_list.append(dic)
                for elem in partner_list:
                    if elem['partner_id'] == partner_id:
                        amt_due_tot = amt_due + elem[month_year]
                        # print("CIO", j["company_name"], chk_in, chk_out)
                        elem.update({month_year: amt_due_tot})
            else:
                for elem in partner_list:

                    if elem['partner_id'] == partner_id:
                        if month_year in elem.keys():
                            amt_due_tot = amt_due + elem[month_year]
                        else:
                            month_year = last_month
                            amt_due_tot = amt_due + elem[month_year]

                        # print("CIO", j["company_name"], chk_in, chk_out)
                        elem.update({month_year: amt_due_tot})

        print("Partner List", partner_list)

        i=0
        for rec in partner_list:
            i = i+1
            print("DL", len(rec))
            keys_list = list(rec)
            heading={
                "customer": "Customer Name",
                "currency": "Curr.$",
            }
            detail = {
                "customer": rec["partner_name"],
                "currency": rec["currency"],
                "advance": rec["advance"]
            }
            if len(rec)>4:
                detail["one"] = list(rec.values())[4]
                one_key = keys_list[4]
                heading["one_head"] = one_key
            if len(rec)>5:
                detail["two"] = list(rec.values())[5]
                two_key = keys_list[5]
                heading["two_head"] = two_key
            if len(rec)>6:
                detail["three"] = list(rec.values())[6]
                three_key = keys_list[6]
                heading["three_head"] = three_key
            if len(rec)>7:
                detail["four"] = list(rec.values())[7]
                four_key = keys_list[7]
                heading["four_head"] = four_key
            if len(rec)>8:
                detail["five"] = list(rec.values())[8]
                five_key = keys_list[8]
                heading["five_head"] = five_key
            if len(rec)>9:
                detail["six"] = list(rec.values())[9]
                six_key = keys_list[9]
                heading["six_head"] = six_key
            if len(rec)>10:
                detail["seven"] = list(rec.values())[10]
                seven_key = keys_list[10]
                heading["seven_head"] = seven_key
            if len(rec)>11:
                detail["eight"] = list(rec.values())[11]
                eight_key = keys_list[11]
                heading["eight_head"] = eight_key
            if len(rec)>12:
                detail["nine"] = list(rec.values())[12]
                nine_key = keys_list[12]
                heading["nine_head"] = nine_key
            if len(rec)>13:
                detail["ten"] = list(rec.values())[13]
                ten_key = keys_list[13]
                heading["ten_head"] = ten_key
            if i==1:
                print("Heading", heading)
                in_out_obj = self.env['cus.sum.aging.report.detail'].create(heading)
                list_rec.append(in_out_obj.id)
                return_obj += self.env['cus.sum.aging.report.detail'].browse(in_out_obj.id)
            in_out_obj = self.env['cus.sum.aging.report.detail'].create(detail)
            list_rec.append(in_out_obj.id)
            return_obj += self.env['cus.sum.aging.report.detail'].browse(in_out_obj.id)
        #
        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        # self.run_process()
        return self.env.ref('teeni_crm.action_customer_sum_aging_report').report_action(self)


class ReportDetail(models.Model):
    _name = 'cus.sum.aging.report.detail'

    customer = fields.Char(readonly=True)
    currency = fields.Char(readonly=True)
    advance = fields.Float(readonly=True)
    one = fields.Float(readonly=True)
    two = fields.Float(readonly=True)
    three = fields.Float(readonly=True)
    four = fields.Float(readonly=True)
    five = fields.Float(readonly=True)
    six = fields.Float(readonly=True)
    seven = fields.Float(readonly=True)
    eight = fields.Float(readonly=True)
    nine = fields.Float(readonly=True)
    ten = fields.Float(readonly=True)

    one_head = fields.Char(readonly=True)
    two_head = fields.Char(readonly=True)
    three_head = fields.Char(readonly=True)
    four_head = fields.Char(readonly=True)
    five_head = fields.Char(readonly=True)
    six_head = fields.Char(readonly=True)
    seven_head = fields.Char(readonly=True)
    eight_head = fields.Char(readonly=True)
    nine_head = fields.Char(readonly=True)
    ten_head = fields.Char(readonly=True)
