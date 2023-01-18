from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar


class ProfitReport(models.TransientModel):
    _name = 'teeni.profit.report.wiz'

    customer_id = fields.Many2one('res.partner')
    from_date = fields.Date()
    to_date = fields.Date()
    product_id = fields.Many2one('product.product')

    rec_lines = fields.Many2many('teeni.profit.report.detail')

    def run_process(self):
        list_rec = []
        return_obj = self.env['teeni.profit.report.detail']
        whr_qry = ''

        if self.customer_id:
            whr_qry += ''' and p.id='''+str(self.customer_id.id)
        if self.from_date:
            whr_qry += ''' and s.confirmation_date>='%s' ''' % self.from_date.strftime('%Y-%m-%d 00:00:00')
        if self.to_date:
            whr_qry += ''' and s.confirmation_date<='%s' ''' % self.to_date.strftime('%Y-%m-%d 23:59:59')
        if self.product_id:
            whr_qry += ''' and pp.id='''+str(self.product_id.id)

        query = '''select s.name as sale_order, p.name as customer, s.confirmation_date, pt.name as product,
                '' as lot,d.qty_delivered, d.price_unit, coalesce(d.avg_cost,0) as avg_cost from sale_order s, sale_order_line d, res_partner p,
                product_product pp,product_template pt
                where s.id = d.order_id and d.product_id = pp.id and pp.product_tmpl_id = pt.id
                and s.partner_id = p.id and d.qty_delivered > 0 and pt.tracking != 'lot'
                and s.state in ('sale', 'done')'''+whr_qry+'''

                union all

                select s.name as sale_order,p.name as customer,s.confirmation_date,pt.name as product,
                lot.name as lot,ml.qty_done as qty_delivered,d.price_unit,coalesce(lot.cost,0) as avg_cost from sale_order s,sale_order_line d,res_partner p,product_product pp,
                product_template pt,stock_move m,stock_move_line ml,stock_production_lot lot where s.id=d.order_id and d.product_id=pp.id and pp.product_tmpl_id=pt.id
                and s.partner_id=p.id and d.qty_delivered>0 and d.id=m.sale_line_id and m.id=ml.move_id and lot.id=ml.lot_id
                and ml.state='done' and pt.tracking = 'lot' and s.state in ('sale', 'done') '''+ whr_qry
        self._cr.execute(query)
        query_res = self._cr.dictfetchall()

        for rec in query_res:
            detail = {
                'sale_order': rec['sale_order'],
                'customer_name': rec['customer'],
                'sale_date': rec['confirmation_date'],
                'item_name': rec['product'],
                'lot': rec['lot'],
                'qty': rec['qty_delivered'],
                'unit_price': rec['price_unit'],
                'cost': rec['avg_cost'],
                'profit': rec['qty_delivered'] * (rec['price_unit'] - rec['avg_cost'])
            }
            in_out_obj = self.env['teeni.profit.report.detail'].create(detail)
            list_rec.append(in_out_obj.id)
            return_obj += self.env['teeni.profit.report.detail'].browse(in_out_obj.id)

        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_profit_report').report_action(self)

class ProfitReportDetail(models.Model):
    _name = 'teeni.profit.report.detail'

    sale_order = fields.Char(readonly=True)
    customer_name = fields.Char(readonly=True)
    sale_date = fields.Char(readonly=True)
    item_name = fields.Char(readonly=True)
    lot = fields.Char(readonly=True)
    qty = fields.Char(readonly=True)
    unit_price = fields.Float(readonly=True)
    cost = fields.Float(readonly=True)
    profit = fields.Float(readonly=True)
