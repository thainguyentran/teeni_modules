# -*- coding: utf-8 -*-
from calendar import monthrange
from datetime import datetime, date, timedelta
from odoo import models, fields, api, osv, _
from odoo.addons import decimal_precision as dp
from odoo.osv import expression
from odoo.exceptions import AccessError, UserError, ValidationError, Warning
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import time
import logging

_logger = logging.getLogger(__name__)


class PartnerArea(models.Model):
    _name = "partner.area"

    district_no = fields.Integer()
    name = fields.Char()
    postal_code = fields.Char()


class PartnerArea(models.Model):
    _name = "partner.region"

    name = fields.Char()
    # monday = fields.Boolean()
    # tuesday = fields.Boolean()
    # wednessday = fields.Boolean()
    # thursday = fields.Boolean()
    # friday = fields.Boolean()
    max_no_of_order = fields.Integer(default=26, string="Max No Of Order in a Day")

    rec_lines = fields.One2many('partner.region.line', 'partner_region_id')


class PartnerAreaLine(models.Model):
    _name = "partner.region.line"

    partner_region_id = fields.Many2one('partner.region')
    partner_area_id = fields.Many2one('partner.area', string="Area")
    district_no = fields.Integer(related="partner_area_id.district_no")


class DORotation(models.Model):
    _name = 'do.rotation.policy'

    month = fields.Selection([(1, 'January'),
                              (2, 'February'),
                              (3, 'March'),
                              (4, 'April'),
                              (5, 'May'),
                              (6, 'June'),
                              (7, 'July'),
                              (8, 'August'),
                              (9, 'September'),
                              (10, 'October'),
                              (11, 'November'),
                              (12, 'December')], default=datetime.now().month, required=1)
    year = fields.Selection([(num, str(num)) for num in range(2021, datetime.now().year + 2)], 'Year',
                            default=datetime.now().year, required=1)
    start_date = fields.Date(required=1)
    region_ids = fields.Many2many('partner.region', string="Region")
    rec_lines = fields.One2many('do.rotation.policy.line', 'rotation_policy_id', string="Rotation Days")
    name = fields.Char(compute='_compute_name')

    @api.depends('month', 'year')
    def _compute_name(self):
        if self.month and self.year:
            self.name = str(dict(self._fields['month'].selection).get(self.month)) + '-' + str(self.year)

    @api.onchange('start_date', 'region_ids', 'month', 'year')
    def OnchangeDate(self):
        if self.start_date and self.region_ids and self.month and self.year:
            self.month = self.start_date.month
            self.year = self.start_date.year

            s_date = self.start_date

            first_day = s_date.day
            num_days = monthrange(self.year, self.month)[1]
            region_length = len(self.region_ids)
            region_index = 0
            add_days = 0
            lines_list = []
            holiday_list = []
            holiday = self.env['hr.holiday.public'].search([('name', '=', self.year), ('state', '=', 'validated')])
            if holiday:
                holiday_lines = self.env['hr.holiday.lines'].search([('holiday_id', '=', holiday.id)])
                for h in holiday_lines:
                    holiday_list.append(h.holiday_date)
            sat_list = []
            get_alternate_saturday = self.env['alternative.working.days.line'].search([])
            for rec in get_alternate_saturday:
                sat_list.append(rec.date)
            print("Alternate Saturday", sat_list)
            print(self.region_ids, first_day, num_days, s_date)
            for day in range(first_day, num_days + 1):

                if region_index == region_length:
                    region_index = 0
                region_id = self.region_ids.ids[region_index]
                new_date = s_date + timedelta(days=add_days)
                # print("Date Type", type(new_date))
                rp = self.env['do.rotation.policy.line']

                if (new_date.weekday() < 5 or new_date in sat_list) and (new_date not in holiday_list):
                    lines_list.append(rp.create({
                        'partner_region_id': region_id,
                        'date': new_date,
                        'week_day': new_date.weekday(),
                        'day': new_date.strftime("%A")
                    }).id)
                    region_index = region_index + 1
                add_days = add_days + 1
            print("Lines List", lines_list)
            self.rec_lines = [(6, 0, lines_list)]


class PartnerAreaLine(models.Model):
    _name = "do.rotation.policy.line"

    rotation_policy_id = fields.Many2one('do.rotation.policy')
    partner_region_id = fields.Many2one('partner.region')
    date = fields.Date()
    week_day = fields.Integer()
    day = fields.Char()


class Partner(models.Model):
    _inherit = "res.partner"

    store_code = fields.Char(string="Store Code")
    customer_price_list = fields.One2many('teeni.customer.price.list', 'partner_id')
    po_expiry_days = fields.Integer(default="0")
    sales_person = fields.Many2one('hr.employee')
    destination_id = fields.Char()
    store_address_1 = fields.Char("Address 1")
    store_address_2 = fields.Char("Address 2")
    store_address_3 = fields.Char("Address 3")
    store_address_4 = fields.Char("Address 4")

    area_id = fields.Many2one('partner.area')
    district_no = fields.Integer(related="area_id.district_no")

    teeni_supplier_id = fields.Char(string="Supplier ID")
    teeni_customer_id = fields.Char(string="Customer ID")
    supplier_group_code = fields.Selection([
        ('TCET', 'TRADE CREDITOR - EXTERNAL'),
        ('TCIC', 'TRADE CREDITOR - INTERNAL'),
        ('NTCE', 'NON TRADE CREDITOR - EXTERNAL'),
        ('NTIC', 'NON TRADE CREDITOR - INTERNAL'),
        ('NCHD', 'NON-TC-HOLDING'),
        ('NCIC', 'NON-TC-INTERCO'),
        ('NCRP', 'NON-TC-RELATED PARTY'),
        ('NCUH', 'NON-TC-ULTIMATE HOLD'),
        ('NONTRADE', 'NON TRADE CREDITOR'),
        ('OTHER', 'OTHER CREDITORS'),
        ('RELATED', 'RELATED COMPANY'),
        ('TCRP', 'TC-RELATED PARTIES')
    ], string="Supplier Group Code")
    supplier_area_code = fields.Selection([
        ('S1', 'EXTERNAL - LOCAL'),
        ('S2', 'EXTERNAL - OVERSEAS'),
        ('S3', 'INTERNAL - LOCAL'),
        ('S4', 'INTERNAL - OVERSEAS')
    ], string="Supplier Area Code")

    customer_group_code = fields.Selection([
        ('TDET', 'TRADE DEPTOR - EXTERNAL'),
        ('TDIC', 'TRADE DEPTOR - INTERNAL'),
        ('NTDE', 'NON TRADE DEPTOR - EXTERNAL'),
        ('NTDI', 'NON TRADE DEPTOR - INTERNAL')
    ], string="Customer Group Code")
    customer_area_code = fields.Selection([
        ('C1', 'EXTERNAL - LOCAL'),
        ('C2', 'EXTERNAL - OVERSEAS'),
        ('C3', 'INTERNAL - LOCAL'),
        ('C4', 'INTERNAL - OVERSEAS')
    ], string="Customer Area Code")
    grn_no = fields.Char(string="GRN No")
    po_term_id = fields.Many2one('teeni.po.term', string="PO Terms")

    name = fields.Char()
    monday = fields.Boolean()
    tuesday = fields.Boolean()
    wednessday = fields.Boolean()
    thursday = fields.Boolean()
    friday = fields.Boolean()

    is_fixed_day_schedule = fields.Boolean()

    @api.model
    def create(self, vals):
           res = super(Partner, self).create(vals)
           res.geo_localize()
           return res
    @api.multi
    def name_get(self):
        res = []
        for partner in self:
            name = partner._get_name()
            if partner.store_code:
                name = partner.store_code + ' ' + name
            res.append((partner.id, name))
        return res

    @api.multi
    def update_area(self):
        qry = """update res_partner set area_id = (select ID from partner_area where postal_code like CONCAT('%',LEFT(res_partner.zip, 2),'%'))
                 where customer='True' and active='True' and length(Zip)>0"""
        self._cr.execute(qry)

    previous_credit = fields.Float()
    previous_debit = fields.Float()

    def get_previous_balance(self, date_from):
        tables, where_clause, where_params = self.env['account.move.line'].with_context(state='posted',
                                                                                        company_id=self.env.user.company_id.id)._query_get()
        where_params = [tuple(self.ids)] + where_params
        print("Tables ", tables)
        print("Params ", where_params)
        print("Where Claus", where_clause)
        if date_from:
            where_clause = " account_move_line__move_id.date<'" + str(date_from) + "' AND" + where_clause
        if where_clause:
            where_clause = 'AND ' + where_clause
        self._cr.execute("""SELECT account_move_line.partner_id, act.type, SUM(account_move_line.amount_residual)
                          FROM """ + tables + """
                          LEFT JOIN account_account a ON (account_move_line.account_id=a.id)
                          LEFT JOIN account_account_type act ON (a.user_type_id=act.id)
                          WHERE act.type IN ('receivable','payable')
                          AND account_move_line.partner_id IN %s
                          AND account_move_line.reconciled IS FALSE
                          """ + where_clause + """
                          GROUP BY account_move_line.partner_id, act.type
                          """, where_params)
        for pid, type, val in self._cr.fetchall():
            partner = self.browse(pid)
            if type == 'receivable':
                return val
            elif type == 'payable':
                return -val


class CustomerPriceList(models.Model):
    _name = 'teeni.customer.price.list'
    _rec_name = 'search_name'

    partner_id = fields.Many2one('res.partner', domain="[('customer', '=', True),('parent_id', '=', False)]")
    product_id = fields.Many2one('product.product', required=True)
    customer_display_code = fields.Char(required=True)
    product_display_name = fields.Char(required=True)
    unit_price = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.user.company_id.currency_id.id,
                                  required=True)
    remarks = fields.Text()
    retail_price = fields.Float(digits=dp.get_precision('Product Price'), default=0.0)

    search_name = fields.Char(compute="_compute_fields_combination")

    @api.onchange('product_id')
    def _on_change_product(self):
        for rec in self:
            rec.product_display_name = rec.product_id.name

    @api.depends('customer_display_code', 'product_display_name')
    def _compute_fields_combination(self):
        for rec in self:
            rec.search_name = ""
            if rec.customer_display_code:
                rec.search_name = "[" + rec.customer_display_code + '] '
            if rec.product_display_name:
                rec.search_name += rec.product_display_name

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        domain = args or []
        prod = self._search(expression.AND([domain, [('customer_display_code', operator, name)]]), limit=limit,
                            access_rights_uid=name_get_uid)
        prod += self._search(expression.AND([domain, [('product_display_name', operator, name)]]), limit=limit,
                             access_rights_uid=name_get_uid)
        rec = self._search([('id', 'in', prod)], limit=limit, access_rights_uid=name_get_uid)

        return self.browse(rec).name_get()


class Sale_Order(models.Model):
    _inherit = 'sale.order'

    base_currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)
    total_in_base_currency = fields.Float()
    cus_po_num = fields.Char(string='Customer PO Number')
    teeni_delivery_date = fields.Date(string="Last Day of Delivery")

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment terms
        - Invoice address
        - Delivery address
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'user_id': self.partner_id.user_id.id or self.partner_id.commercial_partner_id.user_id.id or self.env.uid
        }
        if self.env['ir.config_parameter'].sudo().get_param(
            'sale.use_sale_note') and self.env.user.company_id.sale_note:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note

        if self.partner_id.team_id:
            values['team_id'] = self.partner_id.team_id.id
        self.update(values)
        for rec in self:
            current_date = fields.date.today()
            new_date = current_date + timedelta(days=rec.partner_id.po_expiry_days)
            rec.validity_date = new_date

    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        company_id = self.company_id.id
        journal_id = (self.env['account.invoice'].with_context(company_id=company_id or self.env.user.company_id.id)
            .default_get(['journal_id'])['journal_id'])
        if not journal_id:
            raise UserError(_('Please define an accounting sales journal for this company.'))
        vinvoice = self.env['account.invoice'].new({'partner_id': self.partner_invoice_id.id})
        # Get partner extra fields
        vinvoice._onchange_partner_id()
        invoice_vals = vinvoice._convert_to_write(vinvoice._cache)
        invoice_vals.update({
            'name': self.client_order_ref or '',
            'origin': self.name,
            'type': 'out_invoice',
            'account_id': self.partner_invoice_id.property_account_receivable_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'journal_id': journal_id,
            'currency_id': self.pricelist_id.currency_id.id,
            'comment': self.note,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'company_id': company_id,
            'user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'base_currency_id': self.base_currency_id.id,
            'total_in_base_currency': self.total_in_base_currency,
            'cus_po_number': self.cus_po_num
        })
        return invoice_vals

    @api.onchange('amount_total', 'order_line', 'taxes_id', 'amount_untaxed')
    def _calculate_base_currency(self):
        print("Change")
        if self.currency_id:
            cr = self.currency_id.rate
            self.total_in_base_currency = self.amount_total / cr

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type,
                                      toolbar=toolbar, submenu=submenu)
        if toolbar:
            for action in res['toolbar'].get('action'):
                if action.get('xml_id'):
                    print("XML", action['xml_id'], " CC ", self.id, self._context.get('invoice_count'))
                    if action['xml_id'] == 'sale.action_view_sale_advance_payment_inv':
                        res['toolbar']['action'].remove(action)
        return res


class Sale_Order_line(models.Model):
    _inherit = 'sale.order.line'
    #
    # def _add_domain(self):
    #     print('PID', self.order_id.partner_id.id)
    #     return [('partner_id', 'in', self.order_id.partner_id.id)]
    # customer_display_code = fields.Many2one('teeni.customer.price.list'
    #     # , domain=[('partner_id', 'in', lambda self: self.order_id.partner_id.id)]
    #       #, domain=_add_domain
    #                                         )  # fields.Char()
    partner_id = fields.Many2one('res.partner', related="order_id.partner_id")
    # def _domainproduct(self,partner):
    #     lst = []
    #     print(partner)
    #     if self.order_id.partner_id:
    #         emp_record_de = self.env['teeni.customer.price.list'].search(
    #             [('partner_id', '=', self.order_id.partner_id.id)])
    #         for prod in emp_record_de:
    #             lst.append(prod.product_id.id)
    #
    #     return  [('id', 'in', lst)]

    # , domain = [('sale_ok', '=', True), ()]
    # product_id = fields.Many2one('product.product', string='Product',
    #                              change_default=True, ondelete='restrict',
    #                              domain=lambda self:[('id','in',self.env['teeni.customer.price.list'].search(
    #             [('partner_id', '=', self.partner_id.id)]).product_id.id)])
    customer_display_code = fields.Many2one('teeni.customer.price.list', ondelete='restrict')  # fields.Char()
    price_list_price = fields.Monetary(string="Price in Pricelist", store=True, readonly=True)
    price_list_currency_id = fields.Many2one('res.currency', 'Currency')
    avg_cost = fields.Float()

    @api.onchange('partner_id')
    def domainprod(self):
        lst = []
        print(self.order_id.partner_id)
        if self.order_id.partner_id:
            emp_record_de = self.env['teeni.customer.price.list'].search(
                [('partner_id', '=', self.order_id.partner_id.id)])
            for prod in emp_record_de:
                lst.append(prod.product_id.id)

        return {'domain': {'product_id': [('id', 'in', lst)]}}

    @api.onchange('partner_id')
    def domainprodcode(self):
        lst = []
        print(self.order_id.partner_id)
        if self.order_id.partner_id:
            emp_record_de = self.env['teeni.customer.price.list'].search(
                [('partner_id', '=', self.order_id.partner_id.id)])
            for prod in emp_record_de:
                lst.append(prod.id)
        print(lst)
        return {'domain': {'customer_display_code': [('id', 'in', lst)]}}

    @api.multi
    @api.onchange('customer_display_code')
    def product_code_change(self):
        for rec in self:
            rec.product_id = rec.customer_display_code.product_id

    @api.multi
    @api.onchange('product_id')
    def product_id_change_cost(self):
        product_id = self.env["product.product"].search([('product_tmpl_id', '=', self.product_id.id)], limit=1)
        self.avg_cost = product_id.average_cost_price
        print("Avg Cost", product_id.average_cost_price)

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.attribute_value_id not in self.product_id.product_tmpl_id._get_valid_product_attribute_values():
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav.product_attribute_value_id not in self.product_id.product_tmpl_id._get_valid_product_attribute_values():
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        result = {'domain': domain}

        name = self.get_sale_order_line_multiline_description_sale(product)

        vals.update(name=name)

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
        self.update(vals)

        title = False
        message = False
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s") % product.name
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False
        for rec in self.order_id.partner_id.customer_price_list:
            if rec.product_id.id == self.product_id.id:
                vals['name'] = rec.product_display_name
                vals['price_list_price'] = rec.unit_price
                vals['customer_display_code'] = rec.customer_display_code
                self.update({
                    'name': rec.product_display_name,
                    'price_list_currency_id': rec.currency_id.id,
                    'price_list_price': rec.unit_price,
                    'customer_display_code': rec.id,
                    'price_unit': rec.unit_price

                })
        self.tax_id = self.order_id.taxes_id

        return result

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        res = {}
        product = self.product_id.with_context(force_company=self.company_id.id)
        account = product.property_account_income_id or product.categ_id.property_account_income_categ_id

        if not account and self.product_id:
            raise UserError(
                _('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (self.product_id.name, self.product_id.id, self.product_id.categ_id.name))

        fpos = self.order_id.fiscal_position_id or self.order_id.partner_id.property_account_position_id
        if fpos and account:
            account = fpos.map_account(account)

        res = {
            'name': self.name,
            'sequence': self.sequence,
            'origin': self.order_id.name,
            'account_id': account.id,
            'price_unit': self.price_unit,
            'quantity': qty,
            'discount': self.discount,
            'uom_id': self.product_uom.id,
            'product_id': self.product_id.id or False,
            'invoice_line_tax_ids': [(6, 0, self.tax_id.ids)],
            'account_analytic_id': self.order_id.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'display_type': self.display_type,
            'qty_demanded': self.product_uom_qty,
            'price_list_price': self.price_list_price
        }
        return res


class Account_Invoice(models.Model):
    _inherit = 'account.invoice'

    date_invoice = fields.Date(required=True, string="Invoice Date")
    return_no = fields.Char(string="Reference No")
    return_remarks = fields.Selection([
        ('item_damaged', 'Item Damaged'),
        ('item_expired', 'Item Expired'),
        ('promotion_end', 'Promotion End'),
        ('store_return', 'Store Return'),
        ('item_discontinued', 'Item Discontinued'),
        ('sales_support', 'Sales Support'),
        ('sales_rebate', 'Sales Rebate'),
        ('cost_sharing', 'Promotion – Cost Sharing'),
        ('campaign', 'Campaign / Display'),
        ('Others', 'Others'),

    ])
    base_currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)
    total_in_base_currency = fields.Float()

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(Account_Invoice, self)._onchange_partner_id()
        self.user_id = self.partner_id.user_id.id
        return res

    cus_po_number = fields.Char(string='Customer PO Number')
    payment_status = fields.Selection(
        [('N', 'Not paid'),
         ('F', 'Full'),
         ('P', 'Partial')],
        string="Invoice Payment Status", compute='_get_payment_status')

    @api.onchange('amount_total', 'currency_id', 'invoice_line_ids')
    def _calculate_base_currency(self):
        if self.currency_id:
            cr = self.currency_id.rate
            self.total_in_base_currency = self.amount_total / cr

    @api.one
    @api.depends('residual')
    def _get_payment_status(self):
        if self.residual != 0:
            self.payment_status = 'P'
        elif self.residual == 0 and self.state == 'paid':
            self.payment_status = 'F'
        elif self.residual == 0:
            self.payment_status = 'N'

    salesoption = fields.Selection(
        [('retailsales', 'Retail Sales'), ('othersales', 'Other Sales'), ('exportsales', 'Export Sales')],
        'Department')

    @api.model
    @api.onchange('date_invoice')
    def _get_sequence_prefix(self, refund=True):
        print('invc')
        if self.salesoption == 'retailsales':
            now = datetime.now()
            if self.date_invoice:
                seq = {
                    'prefix': str(self.date_invoice.year) + '/'
                }
            else:
                seq = {
                    'prefix': str(now.year) + '/'
                }
            seqlis = self.env['ir.sequence'].search([('name', '=', 'INV Sequence')]).id
            seqlist = self.env['ir.sequence'].browse(seqlis)
            sequp = seqlist.write(seq)
            return sequp
        if self.salesoption == 'othersales':
            now = datetime.now()
            if self.date_invoice:
                seq = {
                    'prefix': 'IN' + str(self.date_invoice.year) + '/' + str(self.date_invoice.month) + '/',
                }
            else:
                seq = {
                    'prefix': 'IN' + str(now.year) + '/' + str(now.month) + '/',
                }
            seqlis = self.env['ir.sequence'].search([('name', '=', 'INV Sequence')]).id
            seqlist = self.env['ir.sequence'].browse(seqlis)
            sequp = seqlist.write(seq)
            return sequp
        if self.salesoption == 'exportsales':
            now = datetime.now()
            if self.date_invoice:
                seq = {
                    'prefix': 'E' + str(self.date_invoice.year) + '/' + str(self.date_invoice.month) + '/',
                }
            else:
                seq = {
                    'prefix': 'E' + str(now.year) + '/' + str(now.month) + '/',
                }
            seqlis = self.env['ir.sequence'].search([('name', '=', 'INV Sequence')]).id
            seqlist = self.env['ir.sequence'].browse(seqlis)
            sequp = seqlist.write(seq)
            return sequp

    @api.multi
    def print_preview(self):
        return self.env.ref('teeni_crm.action_invoice_print_preview').report_action(self)


class Invoice_Line(models.Model):
    _inherit = 'account.invoice.line'

    price_list_price = fields.Monetary(string="Price in Pricelist", store=True, readonly=True)
    qty_demanded = fields.Float(string="Demanded Quantity", store=True, readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        if not self.invoice_id:
            return

        part = self.invoice_id.partner_id
        fpos = self.invoice_id.fiscal_position_id
        company = self.invoice_id.company_id
        currency = self.invoice_id.currency_id
        type = self.invoice_id.type

        if not part:
            warning = {
                'title': _('Warning!'),
                'message': _('You must first select a partner.'),
            }
            return {'warning': warning}

        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
            if fpos:
                self.account_id = fpos.map_account(self.account_id)
        else:
            self_lang = self
            if part.lang:
                self_lang = self.with_context(lang=part.lang)

            product = self_lang.product_id
            account = self.get_invoice_line_account(type, product, fpos, company)
            if account:
                self.account_id = account.id
            self._set_taxes()

            product_name = self_lang._get_invoice_line_name_from_product()
            if product_name != None:
                self.name = product_name

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

            if company and currency:

                if self.uom_id and self.uom_id.id != product.uom_id.id:
                    self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)

            for rec in self.invoice_id.partner_id.customer_price_list:
                if rec.product_id.id == self.product_id.id:
                    self.name = rec.product_display_name
                    self.price_list_price = rec.unit_price
                    print("INV:" + str(self.price_unit))

        return {'domain': domain}


class Packer_wizard(models.TransientModel):
    _name = 'teeni.packer_wizard'

    packer_id = fields.Many2many('res.users', string="Packer Name", required=1)
    delivery_date = fields.Date(required=1)
    assigned_delivery_date = fields.Date("DO Delivery Date")
    message = fields.Text('Message', readonly=True)

    @api.multi
    def submit(self):
        for rec in self:
            so_id = self.env.context.get('active_id', False)
            self.env['sale.order'].browse(so_id).create_do(rec.packer_id, rec.delivery_date, rec.assigned_delivery_date)
            return {'type': 'ir.actions.act_window_close'}


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # state = fields.Selection(selection_add=[('quotation_revised', 'Quotation Revised')])
    state = fields.Selection([
        ('draft', 'Customer PO'),
        ('sent', 'PO Sent'),
        ('sale', 'DO Created'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('quotation_revised', 'Quotation Revised'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    previous_so = fields.Many2many('prevoius.so', string="Previous So")
    so_previous = fields.Char("Prevoius")
    packer_id = fields.Many2many('res.users', string="Packer Name")
    delivery_date = fields.Date()
    po_term_id = fields.Many2one('teeni.po.term', string='PO Terms')
    taxes_id = fields.Many2many('account.tax', 'sale_order_taxes_rel', 'order_id', 'tax_id',
                                help="Default taxes used when selling the product.", string='Customer Taxes',
                                domain=[('type_tax_use', '=', 'sale')],
                                default=lambda self: self.env.user.company_id.account_sale_tax_id)

    @api.multi
    def get_do_date(self):
    # @api.onchange('date_order')
    # def onchangedodate(self):
        date_order = self.date_order.date()

        if date_order:
            do_rec = self.env['stock.picking']
            year = self.date_order.year
            holiday_list = []
            holiday = self.env['hr.holiday.public'].search(
                [('name', 'in', (year, year + 1)), ('state', '=', 'validated')])
            for hd in holiday:
                holiday_lines = self.env['hr.holiday.lines'].search([('holiday_id', '=', hd.id)])
                for h in holiday_lines:
                    holiday_list.append(h.holiday_date)


            get_day = self.env['partner.region.line'].search(
                [('partner_area_id', '=', self.partner_shipping_id.area_id.id)])
            day_name = []
            new_do_date = None
            current_day_no = date_order.isocalendar()[2]
            print("Current Day No", current_day_no)
            dt = date_order + timedelta(days=current_day_no)
            print("New Date", dt, self.partner_shipping_id.is_fixed_day_schedule)

            ########## Compare date with next delivery date then can add
            day_no = -1
            chk_do_date = None
            tmp_date = None
            region_id = 0
            for d in get_day:
                max_no_of_rec = get_day.partner_region_id.max_no_of_order
                region_id = d.partner_region_id.id
                # if d.partner_region_id.monday:
                if self.partner_shipping_id.is_fixed_day_schedule:
                    week_day_list = []
                    num_of_days = 30
                    if self.partner_shipping_id.monday:
                        week_day_list.append(0)
                    if self.partner_shipping_id.tuesday:
                        week_day_list.append(1)
                    if self.partner_shipping_id.wednessday:
                        week_day_list.append(2)
                    if self.partner_shipping_id.thursday:
                        week_day_list.append(3)
                    if self.partner_shipping_id.friday:
                        week_day_list.append(4)
                    print("Week Day List", week_day_list, max_no_of_rec)
                    if self.po_term_id:
                        num_of_days = self.po_term_id.days
                    print("Num Days", num_of_days)
                    for d in range(1, num_of_days):
                        assign_date = date_order + timedelta(days=d)
                        print("ASss", assign_date)
                        if assign_date.weekday() in week_day_list and assign_date not in holiday_list:
                            count = do_rec.search_count(
                                [('assigned_delivery_date', '=', assign_date), ('state', '!=', 'cancel'),
                                 ('picking_type_id.name', '=', 'Delivery Orders')])
                            print("Count Rec", count, assign_date)
                            if count < max_no_of_rec:
                                chk_do_date = assign_date
                                break

                    print("Final DO Date", chk_do_date)

                if self.partner_shipping_id.is_fixed_day_schedule==False:
                    filter_val = [('date', '>', date_order), ('partner_region_id', '=', region_id), ('rotation_policy_id', '!=', None)]
                    if self.teeni_delivery_date:
                        # total_day = timedelta(self.teeni_delivery_date - date_order).days
                        d1 = datetime.strptime(str(date_order), "%Y-%m-%d")
                        d2 = datetime.strptime(str(self.teeni_delivery_date), "%Y-%m-%d")
                        total_day = abs((d2 - d1).days)
                        print("Total Day", total_day)
                        filter_val.append(tuple(['date', '<=', date_order + timedelta(days=total_day)]))
                    elif self.po_term_id:
                        filter_val.append(tuple(['date', '<=', date_order + timedelta(days=self.po_term_id.days)]))
                    print("Filter Val", filter_val)
                    get_all_dates = self.env['do.rotation.policy.line'].search(filter_val)
                    print("get all dates", get_all_dates)
                    for rpl in get_all_dates:
                        count = do_rec.search_count(
                            [('assigned_delivery_date', '=', rpl.date), ('state', '!=', 'cancel'),
                             ('picking_type_id.name', '=', 'Delivery Orders')])
                        print("DD Rec Count", count, rpl.date)
                        if count < max_no_of_rec:
                            chk_do_date = rpl.date
                            break
                    print("Rotation Date", chk_do_date)
            return chk_do_date

    @api.onchange('taxes_id')
    def on_changes_taxes(self):
        for rec in self.order_line:
            rec.tax_id = self.taxes_id

    def check_delivery_date(self):
        if self.po_term_id and self.delivery_date >= self.date_order.date() + timedelta(days=self.po_term_id.days):
            raise ValidationError(_("Delivery Date need to be within the PO Term."))

    @api.onchange('partner_id')
    def _check_po_term(self):
        self.update(
            {
                'po_term_id': self.partner_id.po_term_id
            })

    def action_request_revise(self):
        p_so = self.env['prevoius.so'].create({
            'name': "SO"
        })
        if not self.so_previous:
            self.so_previous = self.name
        self.previous_so = [(4, p_so.id)]
        x = self.copy()

        prev = len(self.previous_so)

        x.update({
            'name': self.so_previous + '-R' + str(prev),
            'validity_date': self.validity_date,
        })
        self.action_cancel()
        self.state = 'quotation_revised'
        for rec in self:
            sale_action = self.env.ref('sale.action_quotations')
            sale_action = sale_action.read()[0]
            sale_action['domain'] = str([('id', '=', x.id)])
        return sale_action

    def check_validty(self):
        today_date = fields.date.today()

        email_template = self.env.ref('teeni_crm.email_sale_order_validty').id
        sale_order = self.search([('state', '=', 'sale')])
        for rec in sale_order:
            if rec.validity_date:
                if rec.validity_date == today_date:
                    for pick in rec.picking_ids:

                        if pick != 'done':
                            self.env['mail.template'].browse(email_template).send_mail(rec.id, force_send=True)
                            # email_template.send_mail(rec.id)
                elif rec.validity_date < today_date:
                    for pick in rec.picking_ids:
                        if pick != 'done':
                            rec.action_cancel()

    @api.multi
    def action_confirm(self):
        sol = self.env['sale.order.line'].search([('order_id', '=', self.id)])
        message = ""
        for order_line in sol:
            curr = self.env['sale.order.line'].search([('id', '=', order_line.id)], limit=1)
            if curr.product_id.type == 'product':
                precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                product = curr.product_id.with_context(
                    warehouse=curr.order_id.warehouse_id.id,
                    lang=curr.order_id.partner_id.lang or self.env.user.lang or 'en_US'
                )
                product_qty = curr.product_uom._compute_quantity(curr.product_uom_qty, curr.product_id.uom_id)
                if float_compare(product.virtual_available, product_qty, precision_digits=precision) == -1:
                    is_available = curr._check_routing()
                    if not is_available:
                        message = message + _(
                            'You plan to sell %s %s of %s but you only have %s %s available in %s warehouse.') % \
                                  (curr.product_uom_qty, curr.product_uom.name, curr.product_id.name,
                                   product.virtual_available, product.uom_id.name, curr.order_id.warehouse_id.name)
                        # # We check if some products are available in other warehouses.
                        if float_compare(product.virtual_available, curr.product_id.virtual_available,
                                         precision_digits=precision) == -1:
                            message += _('\nThere are %s %s available across all warehouses:\n') % \
                                       (curr.product_id.virtual_available, product.uom_id.name)
                            for warehouse in self.env['stock.warehouse'].search([]):
                                quantity = curr.product_id.with_context(warehouse=warehouse.id).virtual_available
                                if quantity > 0:
                                    message += "- %s: %s %s\n\n" % (
                                        warehouse.name, quantity, curr.product_id.uom_id.name)

        if message:
            context = dict(self.env.context or {})
            context['active_id'] = self.id
            message_id = self.env['message.wizard'].create({'message': message})
            return {
                'name': _('Not enough inventory!'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'message.wizard',
                # pass the id
                'res_id': message_id.id,
                'context': context,
                'target': 'new'
            }

        context = dict(self.env.context or {})
        context['active_id'] = self.id
        do_date = self.get_do_date()

        context['default_assigned_delivery_date'] = do_date
        if not do_date:
            print("DO DATE Msg", do_date)
            context[
                'default_message'] = "All schedule is full in next few days or this is an urgent DO request, please manually adjust this DO date if necessary"

        return {
            'name': 'Packer',
            'type': 'ir.actions.act_window',
            'res_model': 'teeni.packer_wizard',
            # 'view_id': self.env.ref('eastlog.ejr').id,
            'view_mode': 'form',
            'view_type': 'form',
            'context': context,
            'target': 'new',
        }

    @api.multi
    def create_do(self, packer_id, delivery_date, driver_delivery_date):

        print("packer_id", packer_id, "DD", delivery_date)
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])

        packer_list = []
        for p in packer_id:
            packer_list.append(p.id)
        self.write({
            'state': 'sale',
            'confirmation_date': fields.Datetime.now(),
            'packer_id': [(6, 0, packer_list)],
            'delivery_date': delivery_date
        })
        self._action_confirm()
        pick_id = None

        # driver_delivery_date = self.get_do_date()
        for p in self.picking_ids:
            pick_id = p.id
            picking = self.env['stock.picking'].search([('id', '=', pick_id)])
            self.check_delivery_date()
            if picking:
                picking.write({
                    'packer_id': [(6, 0, packer_list)],
                    'date_done': delivery_date
                })
                if picking.picking_type_id.name == 'Delivery Orders':
                    picking.write({'assigned_delivery_date': driver_delivery_date})

        print("Driver Delivery Date", driver_delivery_date)
        if self.env['ir.config_parameter'].sudo().get_param('sale.auto_done_setting'):
            self.action_done()
        if not driver_delivery_date:
            self.delivery_date_alert()

        return True

    @api.multi
    def delivery_date_alert(self):
        print("Driver Delivery Date  -> 2")
        context = dict(self.env.context or {})
        context['active_id'] = self.id
        message_id = self.env['message.wizard'].create({'message': "hgfhtgfgtfgfdg"})
        return {
            'name': _('Not enough inventory!'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'message.wizard',
            # pass the id
            'res_id': message_id.id,
            'context': context,
            'target': 'new'
        }


class MessageWizard(models.TransientModel):
    _name = 'message.wizard'
    message = fields.Text('Message', readonly=True)

    @api.multi
    def action_ok(self):
        context = dict(self.env.context or {})

        so_id = self.env.context.get('active_id', False)
        context['active_id'] = so_id
        sale_order = self.env['sale.order'].search([('id', '=', so_id)])
        do_date = sale_order.get_do_date()
        context['default_assigned_delivery_date'] = do_date
        if not do_date:
            print("DO DATE Msg", do_date)
            context[
                'default_message'] = "All schedule is full in next few days or this is an urgent DO request, please manually adjust this DO date if necessary"
        return {
            'name': 'Packer',
            'type': 'ir.actions.act_window',
            'res_model': 'teeni.packer_wizard',
            # 'view_id': self.env.ref('eastlog.ejr').id,
            'view_mode': 'form',
            'view_type': 'form',
            'context': context,
            'target': 'new',
        }
        # """ close wizard"""
        # return {'type': 'ir.actions.act_window_close'}


class prevoiusso(models.Model):
    _name = 'prevoius.so'

    name = fields.Char("Prvoius so")


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice"

    @api.multi
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        if self.advance_payment_method == 'delivered':

            sale_orders.action_invoice_create()
        elif self.advance_payment_method == 'all':

            sale_orders.action_invoice_create({
                'product_uom_qty': sale_orders.order_line.qty_delivered
            })
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError(_(
                        'The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_(
                        "The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(
                    lambda r: not order.company_id or r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(taxes, self.product_id, order.partner_shipping_id).ids
                else:
                    tax_ids = taxes.ids
                context = {'lang': order.partner_id.lang}
                analytic_tag_ids = []
                for line in order.order_line:
                    analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
                so_line = sale_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'analytic_tag_ids': analytic_tag_ids,
                    'tax_id': [(6, 0, tax_ids)],
                    'is_downpayment': True,
                })
                del context
                self._create_invoice(order, so_line, amount)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}


# class invoiceCreate(models.Model):
#     _inherit = 'account.invoice'


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    teeni_supplier_id = fields.Many2one('res.partner', related="order_id.partner_id")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        lst = []
        supplier_info = self.env['product.supplierinfo']._search([
            ('name', '=', self.teeni_supplier_id.id)])
        for i in supplier_info:
            supplier = self.env['product.supplierinfo'].search([('id', '=', int(i))], limit=1)
            lst.append(supplier.product_tmpl_id.id)
        if lst:
            return {'domain': {'product_id': [('id', 'in', lst)]}}

    @api.onchange('product_qty')
    def _check_stock(self):
        for rec in self:
            stock_qty = self.env['product.product'].search([('id', '=', rec.product_id.id)], limit=1).qty_available
            if rec.product_qty + stock_qty > 1000:
                return {
                    'warning': {
                        'title': _('Overstock Warning'),
                        'message': (_(
                            "Please be careful of overstock. Currently in stock for this product: %s") % stock_qty)
                    }
                }

    @api.multi
    def _compute_tax_id(self):
        for line in self:
            fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.supplier_taxes_id.filtered(
                lambda r: not line.company_id or r.company_id == line.company_id)
            # line.taxes_id = fpos.map_tax(taxes, line.product_id, line.order_id.partner_id) if fpos else taxes
            line.taxes_id = self.order_id.taxes_id


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    packer_id = fields.Many2many('res.users', string="Packer Name")


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    fast_code = fields.Char(string="Fast Code")
    department_code = fields.Many2one('department.code', string="Department Code")


class AccountAccount(models.Model):
    _inherit = 'account.account'

    fast_code = fields.Char(string="Fast Code")
    department_code = fields.Many2one('department.code', string="Department Code")
    parent_id = fields.Many2one('account.account', string="Main Account", index=True)


class DepartmentCode(models.Model):
    _name = 'department.code'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    po_payment_status = fields.Selection(
        [('E', 'Exceeded'),
         ('+', 'Partial')
         ], string="PO Payment Status")
    taxes_id = fields.Many2many('account.tax', 'purchase_order_taxes_rel', 'order_id', 'tax_id',
                                help="Default taxes used when purchasing the product.", string='Supplier Taxes',
                                domain=[('type_tax_use', '=', 'purchase')],
                                default=lambda self: self.env.user.company_id.account_purchase_tax_id)

    @api.onchange('taxes_id')
    def on_changes_taxes(self):
        for rec in self.order_line:
            rec.taxes_id = self.taxes_id


class POTerm(models.Model):
    _name = 'teeni.po.term'

    name = fields.Char('PO Terms', required=True)
    note = fields.Char('Description', required=True)
    days = fields.Integer(string='Number of Days', required=True, default=0)

    @api.one
    @api.constrains('days')
    def _check_days(self):
        if self.days < 0:
            raise ValidationError(_("The number of days used for a PO term cannot be negative."))


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    rate = fields.Float(compute="_compute_rate", store="1")

    @api.depends('currency_id')
    def _compute_rate(self):
        for rec in self:
            if not rec.rate:
                rec.rate = rec.currency_id.rate
