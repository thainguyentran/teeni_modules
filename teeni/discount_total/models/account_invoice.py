from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_amount(self):
        discount = 0
        for line in self.invoice_line_ids:
            discount += (line.price_unit * line.quantity * line.discount) / 100
        self.discount = discount
        total = 0
        for line in self.invoice_line_ids:
            total += line.price
        total -= self.discount
        if self.discount_type == 'percentage':
            self.invoice_discount_amount = total * self.discount_rate / 100
        else:
            self.invoice_discount_amount = self.discount_rate

        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids) - self.invoice_discount_amount
        self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id
            amount_total_company_signed = currency_id._convert(self.amount_total, self.company_id.currency_id,
                                                               self.company_id,
                                                               self.date_invoice or fields.Date.today())
            amount_untaxed_signed = currency_id._convert(self.amount_untaxed, self.company_id.currency_id,
                                                         self.company_id, self.date_invoice or fields.Date.today())
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

        print("Inv Amt", self.amount_untaxed, self.invoice_discount_amount, self.amount_total)

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding', 'invoice_line_ids', 'discount_type', 'discount_rate',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def compute_discount(self):
        discount = 0
        for line in self.invoice_line_ids:
            discount += (line.price_unit * line.quantity * line.discount) / 100
        self.discount = discount
        total = 0
        for line in self.invoice_line_ids:
            total += line.price
        total -= self.discount
        if self.discount_type == 'percentage':
            self.invoice_discount_amount = total * self.discount_rate / 100
        else:
            self.invoice_discount_amount = self.discount_rate
        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids) - self.invoice_discount_amount
        self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        discount = 0
        for line in self.invoice_line_ids:
            discount += (line.price_unit * line.quantity * line.discount) / 100
        self.discount = discount
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

        print("Compute Dis Amt", self.amount_untaxed, self.invoice_discount_amount, self.amount_total)

    @api.one
    @api.depends('invoice_line_ids')
    def compute_total_before_discount(self):
        total = 0
        for line in self.invoice_line_ids:
            total += line.price
        self.total_before_discount = total

    discount_type = fields.Selection([('percentage', 'Percentage'), ('amount', 'Amount')], string='Discount Type',
                                     readonly=True, states={'draft': [('readonly', False)]}, default='amount')
    discount_rate = fields.Float(string='Discount Rate', digits=(16, 2),
                                 readonly=True, states={'draft': [('readonly', False)]}, default=0.0)
    discount = fields.Monetary(string='Product Discount', digits=(16, 2), default=0.0,
                               store=True, compute='compute_discount', track_visibility='always')
    total_before_discount = fields.Monetary(string='Total Before Discount', digits=(16, 2), store=True, compute='compute_total_before_discount')

    invoice_discount_amount = fields.Monetary(string='Invoice Discount', digits=(16, 2), store=True,
                                              compute='compute_discount')

    discount_account = fields.Many2one('account.account')

    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def discount_rate_change(self):
        total = 0
        for line in self.invoice_line_ids:
            total += line.price
        total -= self.discount
        if self.discount_type == 'percentage':
            print("Total", total, self.discount_rate)
            self.invoice_discount_amount = total * self.discount_rate / 100
        else:
            self.invoice_discount_amount = self.discount_rate

    # @api.onchange('discount_type', 'discount_rate', 'invoice_lines_ids')
    # def set_lines_discount(self):
    #     if self.discount_type == 'percentage':
    #         for line in self.invoice_line_ids:
    #             line.discount = self.discount_rate
    #     else:
    #         total = discount = 0.0
    #         for line in self.invoice_line_ids:
    #             total += (line.quantity * line.price_unit)
    #         if self.discount_rate != 0:
    #             discount = (self.discount_rate / total) * 100
    #         else:
    #             discount = self.discount_rate
    #         for line in self.invoice_line_ids:
    #             line.discount = discount

    @api.multi
    def button_dummy(self):
        self.set_lines_discount()
        return True


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.one
    @api.depends('quantity', 'price_unit')
    def compute_line_price(self):
        self.price = self.quantity * self.price_unit

    discount = fields.Float(string='Discount (%)', digits=(16, 2), default=0.0)
    price = fields.Float(string='Price', digits=(16, 2), store=True, compute='compute_line_price')
