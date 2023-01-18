from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar


class PurchaseReport(models.TransientModel):
    _name = 'sup.yl.comp.report.wiz'

    supplier_id = fields.Many2one('res.partner')
    from_date = fields.Date()
    to_date = fields.Date()

    tot_year = fields.Integer()
    rec_lines = fields.Many2many('sup.comp.report.detail')

    def run_process(self):
        list_rec = []
        return_obj = self.env['sup.comp.report.detail']
        whr_qry = ''

        if self.supplier_id:
            whr_qry += ''' and rp.id=''' + str(self.supplier_id.id)
        if self.from_date:
            whr_qry += ''' and po.order_date>='%s' ''' % self.from_date.strftime('%Y-%m-%d 00:00:00')
        if self.to_date:
            whr_qry += ''' and po.order_date<='%s' ''' % self.to_date.strftime('%Y-%m-%d 23:59:59')

        query = '''
                    select rp.id,rp.name as supplier,c.name as currency,coalesce(ROUND(sum(po.amount_total)::numeric, 2 ),0) as total_purchase
                    ,cast(date_part('year',po.date_order) as varchar)as purchase_year
                    from res_partner rp,purchase_order po,res_currency c
                    where po.partner_id=rp.id and po.currency_id = c.id and po.state in ('purchase','done')'''+whr_qry+'''
                    group by rp.id,rp.name,c.name,purchase_year order by rp.name asc,purchase_year desc'''

        self._cr.execute(query)
        query_res = self._cr.dictfetchall()
        year_list = []
        comp_list = []
        head_list = []
        for rec in query_res:
            year_dic = {
                "purchase_year": rec["purchase_year"]
            }
            if not any(d["purchase_year"] == rec["purchase_year"] for d in year_list):
                year_list.append(year_dic)
        self.tot_year = len(year_list)
        for rec in query_res:
            dic = {
                "supplier": rec["supplier"],
                "currency": rec["currency"],
                "total_purchase": rec["total_purchase"],
                "purchase_year": rec["purchase_year"],
            }
            for v in year_list:
                dic[v["purchase_year"]] = 0
            if not any(d['supplier'] == rec["supplier"] and d['currency'] == rec["currency"] for d in comp_list):
                comp_list.append(dic)
                for elem in comp_list:
                    if rec["supplier"] == elem['supplier'] and elem['currency'] == rec["currency"]:
                        purchase_tot = rec["total_purchase"] + elem[rec["purchase_year"]]
                        # print("CIO", j["company_name"], chk_in, chk_out)
                        elem.update({rec["purchase_year"]: purchase_tot})
            else:
                for elem in comp_list:
                    if rec["supplier"] == elem['supplier'] and elem['currency'] == rec["currency"]:
                        purchase_tot = rec["total_purchase"] + elem["2021"]
                        # print("CIO", j["company_name"], chk_in, chk_out)
                        elem.update({rec["purchase_year"]: purchase_tot})
        print("Result", comp_list)
        i=0
        for rec in comp_list:
            i = i+1
            print("DL", len(rec))
            keys_list = list(rec)
            heading={
                "supplier": "Supplier Name",
                "currency": "Curr.$",
            }
            detail = {
                "supplier": rec["supplier"],
                "currency": rec["currency"]
            }
            if len(rec)>4:
                detail["one"] = list(rec.values())[4]
                one_key = keys_list[4]
                heading["one"] = one_key
            if len(rec)>5:
                detail["two"] = list(rec.values())[5]
                two_key = keys_list[5]
                heading["two"] = two_key
            if len(rec)>6:
                detail["three"] = list(rec.values())[6]
                three_key = keys_list[6]
                heading["three"] = three_key
            if len(rec)>7:
                detail["four"] = list(rec.values())[7]
                four_key = keys_list[7]
                heading["four"] = four_key
            if len(rec)>8:
                detail["five"] = list(rec.values())[8]
                five_key = keys_list[8]
                heading["five"] = five_key
            if len(rec)>9:
                detail["six"] = list(rec.values())[9]
                six_key = keys_list[9]
                heading["six"] = six_key
            if len(rec)>10:
                detail["seven"] = list(rec.values())[10]
                seven_key = keys_list[10]
                heading["seven"] = seven_key
            if len(rec)>11:
                detail["eight"] = list(rec.values())[11]
                eight_key = keys_list[11]
                heading["eight"] = eight_key
            if len(rec)>12:
                detail["nine"] = list(rec.values())[12]
                nine_key = keys_list[12]
                heading["nine"] = nine_key
            if len(rec)>13:
                detail["ten"] = list(rec.values())[13]
                ten_key = keys_list[13]
                heading["ten"] = ten_key
            if i==1:
                print("Heading", heading)
                in_out_obj = self.env['sup.comp.report.detail'].create(heading)
                list_rec.append(in_out_obj.id)
                return_obj += self.env['sup.comp.report.detail'].browse(in_out_obj.id)
            in_out_obj = self.env['sup.comp.report.detail'].create(detail)
            list_rec.append(in_out_obj.id)
            return_obj += self.env['sup.comp.report.detail'].browse(in_out_obj.id)
        #
        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_supplier_yl_comp_report').report_action(self)


class ReportDetail(models.Model):
    _name = 'sup.comp.report.detail'

    supplier = fields.Char(readonly=True)
    currency = fields.Char(readonly=True)
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
