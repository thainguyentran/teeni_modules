from odoo import models, fields, api, time, _
from odoo.exceptions import Warning, UserError
from datetime import datetime
import calendar

import logging
_logger = logging.getLogger(__name__)


class StockCardActivityReport(models.TransientModel):
    _name = 'stock.card.acty.report.wiz'

    product_id = fields.Many2one('product.product', string="Product")
    stock_code = fields.Char(string="Stock Code")
    from_date = fields.Date()
    to_date = fields.Date()
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse Name")

    rec_lines = fields.Many2many('stock.card.acty.report.detail')
    agv_u_cost = fields.Float()
    balances = fields.Float()

    def run_process(self):
        list_rec = []
        return_obj = self.env['stock.card.acty.report.detail']
        whr_qry = ''
        wh_loc_lst = []
        wh_loc = self.env['stock.warehouse'].search([])
        for rec in wh_loc:
            wh_loc_lst.append(rec.view_location_id.id)
        print("WH Loc List", wh_loc_lst)
        locations = self.env['stock.location'].search(
            [('id', 'child_of', wh_loc_lst)])

        if self.product_id:
            whr_qry += ''' and pp.id=''' + str(self.product_id.id)
        if self.stock_code:
            whr_qry += ''' and pp.default_code=''' + str(self.stock_code)
        if self.warehouse_id:
            # whr_qry += ''' and wh.id=''' + str(self.warehouse_id.id)
            locations = self.env['stock.location'].search(
                [('id', 'child_of', str(self.warehouse_id.id))])

        # if self.from_date:
        #     whr_qry += ''' and aml.date>='%s' ''' % self.from_date.strftime('%Y-%m-%d 00:00:00')
        # if self.to_date:
        #     whr_qry += ''' and aml.date<='%s' ''' % self.to_date.strftime('%Y-%m-%d 23:59:59')

        date_from = self.from_date or '0001-01-01'
        self.to_date = self.to_date or fields.Date.context_today(self)

        self._cr.execute('''
                SELECT pt.name as product,pt.default_code,(select r.name from res_partner r,stock_picking p where r.id=p.partner_id and p.id=move.picking_id) as particular,
                CAST(move.date AS date) date, move.product_id, move.product_qty,
                move.product_uom_qty, move.product_uom, move.reference,move.sale_line_id,move.purchase_line_id,
                move.location_id, move.location_dest_id,
                case when move.location_dest_id in %s
                then coalesce(move.product_qty,0) end as product_in,
                case when move.location_id in %s
                then coalesce(move.product_qty,0) end as product_out,
                case when move.date < %s then True else False end as is_initial
                FROM stock_move move,product_product pp,product_template pt
                WHERE pp.id=move.product_id and pt.id=pp.product_tmpl_id
                and (move.location_id in %s or move.location_dest_id in %s)
                and move.state = 'done' and move.product_id in (%s)
                and CAST(move.date AS date) <= %s
                ORDER BY move.date, move.reference

                ''',(tuple(locations.ids), tuple(locations.ids),
                     date_from, tuple(locations.ids), tuple(locations.ids),
                     self.product_id.id, self.to_date))
        # print('KR', query)
        # self._cr.execute(query)
        query_res = self._cr.dictfetchall()
        in_out_obj = self.env['stock.card.acty.report.detail']
        return_obj = self.env['stock.card.acty.report.detail']
        _logger.debug("QUERRY RES %s", query_res)
        list_rec = []
        self.agv_u_cost = 0
        initial_balance = 0
        in_out_obj = self.env['stock.card.acty.report.detail']
        dic = {}
        for line in query_res:
            if line['is_initial']:
                # initial_balance = initial_balance + line['product_in'] - line['product_out']
                unit_qty = 0
                if line['product_in']:
                    unit_qty = unit_qty + line['product_in']
                if line['product_out']:
                    unit_qty = unit_qty - line['product_out']
                initial_balance = initial_balance + unit_qty
                dic = {
                    'date': None,
                    'stock_code': line['default_code'],
                    'name': line['product'],
                    'trans_type': None,
                    'ref_no': None,
                    'customer': 'STOCK BALANCE B/F',
                    'unit': 0,
                    'currency': None,
                    'unit_cost': 0,
                    'unit_price': 0,
                    'discount': 0,
                    'total': 0,
                    'balances': initial_balance,
                    'agv_u_cost': 0,
                }
        in_out_obj = self.env['stock.card.acty.report.detail'].create(dic)
        list_rec.append(in_out_obj.id)
        return_obj += self.env['stock.card.acty.report.detail'].browse(in_out_obj.id)




        for line in query_res:
            # base_curr = self.env['res.currency'].search([('name', '=', 'SGD')])
            # foreign_curr = self.env['res.currency'].search([('name', '=', line['currency'])])
            # company = self.env['res.company'].browse(self._context.get('company_id')) or self.env['res.users']._get_company()
            # date = fields.Date.today()
            # base_total = foreign_curr._convert(line['total_sale'],base_curr,company,date)
            if not line['is_initial']:
                unit_qty = 0
                if line['product_in']:
                    unit_qty = unit_qty + line['product_in']
                if line['product_out']:
                    unit_qty = unit_qty - line['product_out']
                initial_balance = initial_balance + unit_qty
                currency = ""
                unit_cost = 0
                unit_price = 0
                discount = 0
                total = 0
                avg_u_cost = 0

                if line["sale_line_id"]:
                    so_line = self.env['sale.order.line'].sudo().search([('id', '=', line['sale_line_id'])])
                    unit_price = so_line.price_unit
                    total = so_line.price_unit * unit_qty
                    currency = so_line.currency_id.name
                    avg_u_cost = so_line.avg_cost

                if line["purchase_line_id"]:
                    po_line = self.env['purchase.order.line'].sudo().search([('id', '=', line['purchase_line_id'])])
                    unit_price = po_line.price_unit
                    total = po_line.price_unit * unit_qty
                    currency = po_line.currency_id.name
                    avg_u_cost = 0

                if total < 0:
                    total = total * -1

                dic = {
                    'date': line["date"],
                    'stock_code': line['default_code'],
                    'name': line['product'],
                    'trans_type': None,
                    'ref_no': line['reference'],
                    'customer': line['particular'],
                    'unit': unit_qty,
                    'currency': currency,
                    'unit_cost': 0,
                    'unit_price': unit_price,
                    'discount': 0,
                    'total': total,
                    'balances': initial_balance,
                    'agv_u_cost': avg_u_cost,
                }
                in_out_obj = self.env['stock.card.acty.report.detail'].create(dic)
                list_rec.append(in_out_obj.id)
                return_obj += self.env['stock.card.acty.report.detail'].browse(in_out_obj.id)
        self.rec_lines = [(6, 0, list_rec)]
        return return_obj

    @api.multi
    def print_report(self):
        return self.env.ref('teeni_crm.action_stock_card_activity_report').report_action(self)


class ReportDetail(models.Model):
    _name = 'stock.card.acty.report.detail'

    date = fields.Char(readonly=True)
    stock_code = fields.Char(readonly=True)
    name = fields.Char(readonly=True)
    trans_type = fields.Char(readonly=True)
    ref_no = fields.Char(readonly=True)
    customer = fields.Char(readonly=True)
    unit = fields.Float(readonly=True)
    currency = fields.Char(readonly=True)
    unit_cost = fields.Float(readonly=True)
    unit_price = fields.Float(readonly=True)
    discount = fields.Float(readonly=True)
    total = fields.Float(readonly=True)
    balances = fields.Float(readonly=True)
    avg_u_cost = fields.Float(readonly=True)
