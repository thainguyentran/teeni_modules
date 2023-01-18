from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderImportConfig(models.Model):
    _name = 'sale.order.import.config'
    _description = 'Configuration for the import of Customer Sale Order'
    _order = 'sequence'

    name = fields.Char(required=True)
    partner_id = fields.Many2one(
        'res.partner', ondelete='cascade',
        domain=[('customer', '=', True), ('parent_id', '=', False)])
    active = fields.Boolean(default=True)
    sequence = fields.Integer()
    sale_order_line_method = fields.Selection([
        ('1line_no_product', 'Single Line, No Product'),
        ('1line_static_product', 'Single Line, Static Product'),
        ('nline_no_product', 'Multi Line, No Product'),
        ('nline_static_product', 'Multi Line, Static Product'),
        ('nline_auto_product', 'Multi Line, Auto-selected Product'),
        ], string='Method for Sale Order Line', required=True,
        default='1line_no_product',
        help="The multi-line methods will not work for PDF invoices "
        "that don't have an embedded XML file. "
        "The 'Multi Line, Auto-selected Product' method will only work with "
        "ZUGFeRD invoices at Comfort or Extended level, not at Basic level.")
    company_id = fields.Many2one(
        'res.company',
        ondelete='cascade', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'sale.order.import.config'))
    account_id = fields.Many2one(
        'account.account', string='Expense Account',
        domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account')
    label = fields.Char(
        string='Force Description',
        help="Force customer sale order line description")
    tax_ids = fields.Many2many(
        'account.tax', string='Taxes',
        domain=[('type_tax_use', '=', 'sale')])
    static_product_id = fields.Many2one('product.product')
    static_uom_id = fields.Many2one('uom.uom')

    @api.constrains('sale_order_line_method', 'account_id', 'static_product_id')
    def _check_import_config(self):
        for config in self:
            if (
                    'static_product' in config.sale_order_line_method and
                    not config.static_product_id):
                raise ValidationError(_(
                    "Static Product must be set on the invoice import "
                    "configuration of Customer '%s' that has a Method "
                    "for Sale Order Line set to 'Single Line, Static Product' "
                    "or 'Multi Line, Static Product'.")
                    % config.partner_id.name)
            if (
                    'no_product' in config.sale_order_line_method and
                    not config.account_id):
                raise ValidationError(_(
                    "The Expense Account must be set on the Sale Order "
                    "import configuration of Customer '%s' that has a "
                    "Method for Sale Order Line set to 'Single Line, No Product' "
                    "or 'Multi Line, No Product'.")
                    % config.partner_id.name)

    @api.onchange('sale_order_line_method', 'account_id')
    def sale_order_line_method_change(self):
        if (
                self.sale_order_line_method == '1line_no_product' and
                self.account_id):
            self.tax_ids = [(6, 0, self.account_id.tax_ids.ids)]
        elif self.sale_order_line_method != '1line_no_product':
            self.tax_ids = [(6, 0, [])]

    def convert_to_import_config(self):
        self.ensure_one()
        vals = {
            'sale_order_line_method': self.sale_order_line_method,
            'account_analytic': self.account_analytic_id or False,
            }
        if self.sale_order_line_method == '1line_no_product':
            vals['account'] = self.account_id
            vals['taxes'] = self.tax_ids
            vals['label'] = self.label or False
        elif self.sale_order_line_method == '1line_static_product':
            vals['product'] = self.static_product_id
            vals['uom'] = self.static_uom_id
            vals['label'] = self.label or False
        elif self.sale_order_line_method == 'nline_no_product':
            vals['account'] = self.account_id
        elif self.sale_order_line_method == 'nline_static_product':
            vals['product'] = self.static_product_id
        return vals
