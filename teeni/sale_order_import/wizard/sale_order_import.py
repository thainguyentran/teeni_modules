import base64
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare, float_round, float_is_zero, config
from odoo.exceptions import UserError
from lxml import etree
import logging
from datetime import datetime
import mimetypes

logger = logging.getLogger(__name__)


class SaleOrderImport(models.TransientModel):
    _name = 'sale.order.import'
    _description = 'Wizard to import supplier Sale Orders/refunds'

    sale_order_file = fields.Binary(
        string='PDF or XML Sale Order', required=True)
    sale_order_filename = fields.Char(string='Filename')
    state = fields.Selection([
        ('import', 'Import'),
        ('config', 'Select Sale Order Import Configuration'),
        ('update', 'Update'),
        ('update-from-sale-order', 'Update From Sale Order'),
        ], default="import")
    partner_id = fields.Many2one(
        'res.partner', string="Customer", readonly=True)
    import_config_id = fields.Many2one(
        'sale.order.import.config', string='Sale Order Import Configuration')
    currency_id = fields.Many2one(
        'res.currency', readonly=True)
    sale_order_type = fields.Char(string="Sale Order Type", readonly=True)
    amount_untaxed = fields.Float(
        string='Total Untaxed', digits=dp.get_precision('Account'),
        readonly=True)
    amount_total = fields.Float(
        string='Total', digits=dp.get_precision('Amount'),
        readonly=True)
    order_id = fields.Many2one(
        'sale.order', string='Draft Customer Sale Order to Update')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # I can't put 'default_state' in context because then it is transfered
        # to the code and it causes problems when we create Sale Order lines
        if self.env.context.get('wizard_default_state'):
            res['state'] = self.env.context['wizard_default_state']
        if (
                self.env.context.get('default_partner_id') and
                not self.env.context.get('default_import_config_id')):
            configs = self.env['sale.order.import.config'].search([
                ('partner_id', '=', self.env.context['default_partner_id']),
                ('company_id', '=', self.env.user.company_id.id),
                ])
            if len(configs) == 1:
                res['import_config_id'] = configs.id
        return res

    @api.model
    def parse_xml_sale_order(self, xml_root):
        return False

    @api.model
    def parse_pdf_sale_order(self, file_data):
        '''This method must be inherited by additional modules with
        the same kind of logic as the account_bank_statement_import_*
        modules'''
        bdio = self.env['business.document.import']
        xml_files_dict = bdio.get_xml_files_from_pdf(file_data)
        for xml_filename, xml_root in xml_files_dict.items():
            logger.info('Trying to parse XML file %s', xml_filename)
            parsed_so = self.parse_xml_sale_order(xml_root)
            if parsed_so:
                return parsed_so
        parsed_so = self.fallback_parse_pdf_sale_order(file_data)
        if not parsed_so:
            raise UserError(_(
                "This type of PDF Sale Order is not supported. Did you install "
                "the module to support this type of file?"))
        return parsed_so

    def fallback_parse_pdf_sale_order(self, file_data):
        '''Designed to be inherited by the module
        sale_order_import_saleorder2data, to be sure the invoice2data
        technique is used after the electronic Sale Order modules such as
        account_Sale Order_import_zugferd
        '''
        return False

        # Sale Order PIVOT format ('parsed_so' without pre-processing)
        # For refunds, we support 2 possibilities:
        # a) type = 'in_Sale Order' with negative amounts and qty
        # b) type = 'in_refund' with positive amounts and qty ("Odoo way")
        # That way, it simplifies the code in the format-specific import
        # modules, which is what we want!
        # {
        # 'type': 'in_Sale Order' or 'in_refund'  # 'in_Sale Order' by default
        # 'currency': {
        #    'iso': 'EUR',
        #    'currency_symbol': u'€',  # The one or the other
        #    },
        # 'date': '2015-10-08',  # Must be a string
        # 'date_due': '2015-11-07',
        # 'date_start': '2015-10-01',  # for services over a period of time
        # 'date_end': '2015-10-31',
        # 'amount_untaxed': 10.0,
        # 'amount_tax': 2.0,  # provide amount_untaxed OR amount_tax
        # 'amount_total': 12.0,  # Total with taxes, must always be provided
        # 'partner': {
        #       'vat': 'FR25499247138',
        #       'email': 'support@browserstack.com',
        #       'name': 'Capitaine Train',
        #       },
        # 'company': {'vat': 'FR12123456789'}, # Rarely set in Sale Orders
        #                                      # Only used to check we are not
        #                                      # importing the Sale Order in the
        #                                      # wrong company by mistake
        # 'Sale Order_number': 'I1501243',
        # 'description': 'TGV Paris-Lyon',
        # 'attachments': {'file1.pdf': base64data1, 'file2.pdf': base64data2},
        # 'chatter_msg': ['Notes added in chatter of the Sale Order'],
        # 'note': 'Note embedded in the document',
        # 'origin': 'Origin note',
        # 'lines': [{
        #       'product': {
        #           'barcode': '4123456000021',
        #           'code': 'GZ250',
        #           },
        #       'name': 'Gelierzucker Extra 250g',
        #       'price_unit': 1.45, # price_unit without taxes
        #       'qty': 2.0,
        #       'price_subtotal': 2.90,  # not required, but needed
        #               to be able to generate adjustment lines when decimal
        #               precision is not high enough in Odoo
        #       'uom': {'unece_code': 'C62'},
        #       'taxes': [{
        #           'amount_type': 'percent',
        #           'amount': 20.0,
        #           'unece_type_code': 'VAT',
        #           'unece_categ_code': 'S',
        #           'unece_due_date_code': '432',
        #           }],
        #       'date_start': '2015-10-01',
        #       'date_end': '2015-10-31',
        #       # date_start and date_end on lines override the global value
        #       }],
        # }

        # IMPORT CONFIG
        # {
        # 'sale_order_line_method': '1line_no_product',
        # 'account_analytic': Analytic account recordset,
        # 'account': Account recordset,
        # 'taxes': taxes multi-recordset,
        # 'label': 'Force Sale Order line description',
        # 'product': product recordset,
        # }
        #
        # Note: we also support importing customer Sale Orders via
        # create_Sale Order() but only with 'nline_*' Sale Order import methods.

    @api.model
    def _prepare_create_sale_order_vals(self, parsed_so, import_config=False):
        assert parsed_so.get('pre-processed'), 'pre-processing not done'
        # WARNING: on future versions, import_config will probably become
        # a required argument
        so = self.env['sale.order']
        sol = self.env['sale.order.line']
        bdio = self.env['business.document.import']
        # rpo = self.env['res.partner']
        # company = self.env['res.company']
        partner = bdio._match_partner(
            parsed_so['partner'], parsed_so['chatter_msg'],
            partner_type='customer')
        # currency = bdio._match_currency(parsed_so.get('currency'), parsed_so['chatter_msg'])
        if parsed_so.get('cus_po_num'):
            existing_orders = so.search([
                ('cus_po_num', '=', parsed_so['cus_po_num']),
                ('partner_id', '=', partner.id),
                ('state', '!=', 'cancel'),
                ])
            if existing_orders:
                raise UserError(_(
                    "An order of customer '%s' with reference '%s' "
                    "already exists: %s (state: %s)") % (
                        partner.display_name,
                        parsed_so['cus_po_num'],
                        existing_orders[0].name,
                        existing_orders[0].state))
        delivery_address = self.env['res.partner'].search([('store_code', 'like', parsed_so['store_code']),('parent_id','=',partner.id)], limit=1)
        if delivery_address:
            vals = {
                'partner_id': partner.id,
                'cus_po_num': parsed_so.get('cus_po_num'),
                'teeni_delivery_date': parsed_so.get('delivery_date'),
                'partner_shipping_id': delivery_address.id
                }
        else:
            vals = {
            'partner_id': partner.id,
            'cus_po_num': parsed_so.get('cus_po_num'),
            'teeni_delivery_date': parsed_so.get('delivery_date')
            }
        vals = so.play_onchanges(vals, ['partner_id'])
        vals['order_line'] = []
        config = import_config  # just to make variable name shorter
        if not config:
            if not partner.sale_order_import_ids:
                raise UserError(_(
                    "Missing Sale Order Import Configuration on partner '%s'.")
                    % partner.display_name)
            else:
                import_config_obj = partner.sale_order_import_ids[0]
                config = import_config_obj.convert_to_import_config()

        if config['sale_order_line_method'].startswith('1line'):
            if config['sale_order_line_method'] == '1line_no_product':
                if config['taxes']:
                    sale_order_line_tax_ids = [(6, 0, config['taxes'].ids)]
                else:
                    sale_order_line_tax_ids = False
                sol_vals = {
                    'order': vals,
                    'sale_order_line_tax_ids': sale_order_line_tax_ids,
                    'price_unit': parsed_so.get('amount_untaxed'),
                    }
            elif config['sale_order_line_method'] == '1line_static_product':
                product = config['product']
                uom = config['uom']
                sol_vals = {
                    'order_id': vals,
                    'price_unit': parsed_so.get('amount_untaxed'),
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'product_uom': uom.id,
                    'price_subtotal': parsed_so.get('total')
                }

                # sol_vals = {'product_id': product.id, 'order': vals}
                sol_vals = sol.play_onchanges(sol_vals, ['product_id'])
                sol_vals.pop('order_id')
            if config.get('label'):
                sol_vals['name'] = config['label']
            elif parsed_so.get('description'):
                sol_vals['name'] = parsed_so['description']
            elif not sol_vals.get('name'):
                sol_vals['name'] = _('MISSING DESCRIPTION')
            self.set_1line_price_unit_and_quantity(sol_vals, parsed_so)
            self.set_1line_start_end_dates(sol_vals, parsed_so)
            vals['order_line'].append((0, 0, sol_vals))
        elif config['sale_order_line_method'].startswith('nline'):

            if not parsed_so['order_line']:
                raise UserError(_(
                    "You have selected a Multi Line method for this import "
                    "but Odoo could not extract/read any XML file inside "
                    "the PDF Sale Order."))
            if config['sale_order_line_method'] == 'nline_no_product':
                static_vals = {
                    'account_id': config['account'].id,
                }
            elif config['sale_order_line_method'] == 'nline_static_product':
                sproduct = config['product']
                static_vals = {'product_id': sproduct.id, 'order_id': vals}
                static_vals = sol.play_onchanges(static_vals, ['product_id'])
                static_vals.pop('order_id')
            else:
                static_vals = {}
            for line in parsed_so['order_line']:
                product = ""
                # product_price = 0
                sol_vals = static_vals.copy()
                if config['sale_order_line_method'] == 'nline_auto_product':
                    ppo = self.env['product.product']
                    cpl = self.env['teeni.customer.price.list']
                    product = ppo
                    c_product = cpl
                    if line.get('cus_code'):
                        c_product = cpl.search([('customer_display_code','=', line['cus_code'])], limit=1)
                        if c_product:
                            product = c_product.product_id
                            # product_price = c_product.unit_price
                        else:
                            product = ppo.search([('barcode', '=', line['cus_code'])], limit=1)
                            # product_price = product.lst_price
                            if not product:
                                raise UserError(_("no matched product for this Customer Display Code '%s'.") % (line['cus_code']))
                    elif line.get('barcode'):
                        product = ppo.search([('barcode', '=', line['barcode'])], limit=1)
                        # product_price = product.lst_price
                        if not product:
                            c_product = cpl.search([('customer_display_code','=', line['barcode'])], limit=1)
                            if c_product:
                                product = c_product.product_id
                                # product_price = c_product.unit_price
                            else:
                                raise UserError(_("no matched product for this barcode '%s'.") % (line['barcode']))
                    # product = bdio._match_product(
                    #     line['product'], parsed_so['chatter_msg'],
                    #     customer=partner)
                    sol_vals = {'product_id': product.id, 'order_id': vals}
                    sol_vals = sol.play_onchanges(sol_vals, ['product_id'])

                    sol_vals.pop('order_id')
                elif config['sale_order_line_method'] == 'nline_no_product':
                    taxes = bdio._match_taxes(
                        line.get('taxes'), parsed_so['chatter_msg'])
                    sol_vals['sale_order_line_tax_ids'] = [(6, 0, taxes.ids)]
                if not sol_vals.get('product_id'):
                    product = self.env['product.product'].browse(
                        sol_vals['product_id'])
                if line.get('name'):
                    sol_vals['name'] = line['name']
                elif not sol_vals.get('name'):
                    sol_vals['name'] = product.display_name
                # if start_end_dates_installed:
                #     sol_vals['start_date'] =\
                #         line.get('date_start') or parsed_so.get('date_start')
                #     sol_vals['end_date'] =\
                #         line.get('date_end') or parsed_so.get('date_end')
                uom = bdio._match_uom(
                    line.get('uom'), parsed_so['chatter_msg'])
                sol_vals['product_uom'] = product.uom_id.id
                # logger.debug("CUSTOMER AC %s", partner.customer_area_code)
                t_tax_id = []
                if partner.customer_area_code in ['C1','C3']:
                    t_tax_id = [6]
                elif partner.customer_area_code in ['C2','C4']:
                    t_tax_id =[5]
                if line.get('pack_qty') and partner.id in [903, 1043, 186,]:
                    sol_vals.update({
                    'product_uom_qty': float(line['Qty']) * float(line['pack_qty']),
                    'price_unit': float(line['Unit_Price'])/float(line['pack_qty']),  # TODO fix for tax incl
                    'price_subtotal': float(line['Unit_Price']) * float(line['Qty']) * float(line['pack_qty']),
                    'tax_id': [(6, 0, t_tax_id)]
                    })
                elif line.get('pack_qty') and partner.id not in [903, 1043, 186,]:
                    sol_vals.update({
                    'product_uom_qty': float(line['Qty']) * float(line['pack_qty']),
                    'price_unit': float(line['Unit_Price']),  # TODO fix for tax incl
                    'price_subtotal': float(line['Unit_Price']) * float(line['Qty']) * float(line['pack_qty']),
                    'tax_id': [(6, 0, t_tax_id)]
                    })
                else:
                    sol_vals.update({
                        'product_uom_qty': float(line['Qty']),
                        'price_unit': line['Unit_Price'],  # TODO fix for tax incl
                        'price_subtotal': float(line['Unit_Price']) * float(line['Qty']),
                        'tax_id': [(6, 0, t_tax_id)]
                        })
                vals['order_line'].append((0, 0, sol_vals))
        # Write analytic account + fix syntax for taxes
        aacount_id = config.get('account_analytic') and\
            config['account_analytic'].id or False
        if aacount_id:
            for line in vals['order_line']:
                line[2]['account_analytic_id'] = aacount_id
        return (vals, config)

    @api.model
    def set_1line_price_unit_and_quantity(self, sol_vals, parsed_so):
        """For the moment, we only take into account the 'price_include'
        option of the first tax"""
        sol_vals['product_uom_qty'] = 1
        sol_vals['price_unit'] = parsed_so.get('amount_total')
        if sol_vals.get('sale_order_line_tax_ids'):
            for tax_entry in sol_vals['sale_order_line_tax_ids']:
                if tax_entry:
                    tax_id = False
                    if tax_entry[0] == 4:
                        tax_id = tax_entry[1]
                    elif tax_entry[0] == 6:
                        tax_id = tax_entry[2][0]
                    if tax_id:
                        first_tax = self.env['account.tax'].browse(tax_id)
                        if not first_tax.price_include:
                            sol_vals['price_unit'] = parsed_so.get(
                                'amount_untaxed')
                            break

    @api.model
    def set_1line_start_end_dates(self, sol_vals, parsed_so):
        """Only useful if you have installed the module account_cutoff_prepaid
        from https://github.com/OCA/account-closing"""
        ailo = self.env['sale.order.line']
        if (
                parsed_so.get('date_start') and
                parsed_so.get('date_end') and
                hasattr(ailo, 'start_date') and
                hasattr(ailo, 'end_date')):
            sol_vals['start_date'] = parsed_so.get('date_start')
            sol_vals['end_date'] = parsed_so.get('date_end')

    def company_cannot_refund_vat(self):
        company_id = self.env.context.get('force_company') or\
            self.env.user.company_id.id
        vat_purchase_taxes = self.env['account.tax'].search([
            ('company_id', '=', company_id),
            ('amount_type', '=', 'percent'),
            ('type_tax_use', '=', 'purchase')])
        if not vat_purchase_taxes:
            return True
        return False

    @api.model
    def parse_sale_order(self, sale_order_file_b64, sale_order_filename):
        assert sale_order_file_b64, 'No Sale Order file'
        logger.info('Starting to import Sale Order %s', sale_order_filename)
        file_data = base64.b64decode(sale_order_file_b64)
        filetype = mimetypes.guess_type(sale_order_filename)
        logger.debug('sale_order mimetype: %s', filetype)
        if filetype and filetype[0] in ['application/xml', 'text/xml']:
            try:
                xml_root = etree.fromstring(file_data)
            except Exception as e:
                raise UserError(_(
                    "This XML file is not XML-compliant. Error: %s") % e)
            pretty_xml_string = etree.tostring(
                xml_root, pretty_print=True, encoding='UTF-8',
                xml_declaration=True)
            logger.debug('Starting to import the following XML file:')
            logger.debug(pretty_xml_string)
            parsed_so = self.parse_xml_sale_order(xml_root)
            if parsed_so is False:
                raise UserError(_(
                    "This type of XML Sale Order is not supported. "
                    "Did you install the module to support this type "
                    "of file?"))
        # Fallback on PDF
        else:
            parsed_so = self.parse_pdf_sale_order(file_data)
        if 'attachments' not in parsed_so:
            parsed_so['attachments'] = {}
        parsed_so['attachments'][sale_order_filename] = sale_order_file_b64
        # pre_process_parsed_so() will be called again a second time,
        # but it's OK
        pp_parsed_so = self.pre_process_parsed_so(parsed_so)
        return pp_parsed_so

    @api.model
    def pre_process_parsed_so(self, parsed_so):
        if parsed_so.get('pre-processed'):
            return parsed_so
        parsed_so['pre-processed'] = True
        if 'chatter_msg' not in parsed_so:
            parsed_so['chatter_msg'] = []
        if parsed_so.get('type') == 'out_sale_order':
            return parsed_so
        prec_ac = self.env['decimal.precision'].precision_get('Account')
        prec_pp = self.env['decimal.precision'].precision_get('Product Price')
        prec_uom = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        if 'amount_tax' in parsed_so and 'amount_untaxed' not in parsed_so:
            parsed_so['amount_untaxed'] =\
                parsed_so['amount_total'] - parsed_so['amount_tax']
        elif (
                'amount_untaxed' not in parsed_so and
                'amount_tax' not in parsed_so):
            # For Sale Orders that never have taxes
            parsed_so['amount_untaxed'] = parsed_so['amount_total']
        # Support the 2 refund methods; if method a) is used, we convert to
        # method b)
        if not parsed_so.get('type'):
            parsed_so['type'] = 'in_sale_order'  # default value
        if (
                parsed_so['type'] == 'in_sale_order' and
                float_compare(
                parsed_so['amount_total'], 0, precision_digits=prec_ac) < 0):
            parsed_so['type'] = 'in_refund'
            for entry in ['amount_untaxed', 'amount_total']:
                parsed_so[entry] *= -1
            for line in parsed_so.get('order_line', []):
                line['qty'] *= -1
                if 'price_subtotal' in line:
                    line['price_subtotal'] *= -1
        # Handle the case where we import an Sale Order with VAT in a company that
        # cannot deduct VAT
        if self.company_cannot_refund_vat():
            parsed_so['amount_tax'] = 0
            parsed_so['amount_untaxed'] = parsed_so['amount_total']
            for line in parsed_so.get('order_line', []):
                if line.get('taxes'):
                    if len(line['taxes']) > 1:
                        raise UserError(_(
                            "You are importing an Sale Order in a company that "
                            "cannot deduct VAT and the imported Sale Order has "
                            "several VAT taxes on the same line (%s). We do "
                            "not support this scenario for the moment.")
                            % line.get('name'))
                    vat_rate = line['taxes'][0].get('amount')
                    if not float_is_zero(vat_rate, precision_digits=2):
                        line['price_unit'] = line['price_unit'] *\
                            (1 + vat_rate/100.0)
                        line.pop('price_subtotal')
                        line['taxes'] = []
        # Rounding work
        for entry in ['amount_untaxed', 'amount_total']:
            parsed_so[entry] = float_round(
                parsed_so[entry], precision_digits=prec_ac)
        # for line in parsed_so.get('order_line', []):
        #     line['Qty'] = float_round(line['Qty'], precision_digits=prec_uom)
        #     line['Unit_Price'] = float_round(
        #         line['Unit_Price'], precision_digits=prec_pp)
        logger.debug('Result of Sale Order parsing parsed_so=%s', parsed_so)
        # the 'company' dict in parsed_so is NOT used to auto-detect
        # the company, but to check that we are not importing an
        # Sale Order for another company by mistake
        # The advantage of doing the check here is that it will be run
        # in all scenarios (create/update/...), but it's not related
        # to Sale Order parsing...
        if (
                parsed_so.get('company') and
                not config['test_enable'] and
                not self.env.context.get('edi_skip_company_check')):
            self.env['business.document.import']._check_company(
                parsed_so['company'], parsed_so['chatter_msg'])
        return parsed_so

    @api.model
    def sale_order_already_exists(self, customer, parsed_so):
        company_id = self.env.context.get('force_company') or\
            self.env.user.company_id.id
        existing_inv = self.env['sale.order'].search([
            ('company_id', '=', company_id),
            ('partner_id', '=', customer.id),
            ('cus_po_num', '=', parsed_so['cus_po_num'])
            ], limit=1)
        return existing_inv

    @api.multi
    def import_sale_order(self):
        """Method called by the button of the wizard
        (import step AND config step)"""
        self.ensure_one()
        aio = self.env['sale.order']
        aiico = self.env['sale.order.import.config']
        bdio = self.env['business.document.import']
        iaao = self.env['ir.actions.act_window']
        company_id = self.env.context.get('force_company') or\
            self.env.user.company_id.id
        parsed_so = self.parse_sale_order(
            self.sale_order_file, self.sale_order_filename)
        partner = bdio._match_partner(
            parsed_so['partner'], parsed_so['chatter_msg'])
        # partner = partner.commercial_partner_id
        currency = bdio._match_currency(
            parsed_so.get('currency'), parsed_so['chatter_msg'])
        parsed_so['partner']['recordset'] = partner
        parsed_so['currency']['recordset'] = currency
        wiz_vals = {
            'partner_id': partner.id,
            'cus_po_num': parsed_so['cus_po_num'],
            'currency_id': currency.id,
            'amount_untaxed': parsed_so['amount_untaxed'],
            'amount_total': parsed_so['amount_total'],
            }

        existing_inv = self.sale_order_already_exists(partner, parsed_so)
        if existing_inv:
            raise UserError(_(
                "This Sale Order already exists in Odoo. It's "
                "Customer PO Number is '%s' and it's SO number "
                "is '%s'")
                % (parsed_so.get('cus_po_num'), existing_inv.name))

        if self.import_config_id:  # button called from 'config' step
            wiz_vals['import_config_id'] = self.import_config_id.id
            import_config = self.import_config_id.convert_to_import_config()
        else:  # button called from 'import' step
            import_configs = aiico.search([
                ('partner_id', '=', partner.id),
                ('company_id', '=', company_id)])
            if not import_configs:
                raise UserError(_(
                    "Missing Sale Order Import Configuration on partner '%s'.")
                    % partner.display_name)
            elif len(import_configs) == 1:
                wiz_vals['import_config_id'] = import_configs.id
                import_config = import_configs.convert_to_import_config()
            else:
                logger.info(
                    'There are %d Sale Order import configs for partner %s',
                    len(import_configs), partner.display_name)

        if not wiz_vals.get('import_config_id'):
            wiz_vals['state'] = 'config'
            action = iaao.for_xml_id(
                'sale_order_import',
                'sale_order_import_action')
            action['res_id'] = self.id
        else:
            draft_same_customer_ord = aio.search([
                ('partner_id', '=', partner.id),
                ('name', '=', parsed_so['cus_po_num']),
                ('state', '=', 'draft'),
                ])
            logger.debug(
                'draft_same_customer_ord=%s', draft_same_customer_ord)
            if draft_same_customer_ord:
                wiz_vals['state'] = 'update'
                if len(draft_same_customer_ord) == 1:
                    wiz_vals['order_id'] = draft_same_customer_ord[0].id
                action = iaao.for_xml_id(
                    'sale_order_import',
                    'sale_order_import_action')
                action['res_id'] = self.id
            else:
                action = self.create_sale_order_action(parsed_so, import_config)
        self.write(wiz_vals)
        return action

    @api.multi
    def create_sale_order_action_button(self):
        '''Workaround for a v10 bug: if I call create_sale_order_action()
        directly from the button, I get the context in parsed_so'''
        return self.create_sale_order_action()

    @api.multi
    def create_sale_order_action(self, parsed_so=None, import_config=None):
        '''parsed_so is not a required argument'''
        self.ensure_one()
        iaao = self.env['ir.actions.act_window']
        if parsed_so is None:
            parsed_so = self.parse_sale_order(
                self.sale_order_file, self.sale_order_filename)
        if import_config is None:
            assert self.import_config_id
            import_config = self.import_config_id.convert_to_import_config()
        sale_order = self.create_sale_order(parsed_so, import_config)
        sale_order.message_post(body=_(
            "This Sale Order has been created automatically via file import"))
        action = iaao.for_xml_id(
            'sale', 'action_quotations')
        action.update({
            'view_mode': 'form,tree,calendar,graph',
            'views': False,
            'view_id': False,
            'res_id': sale_order.id,
            })
        return action

    @api.model
    def create_sale_order(self, parsed_so, import_config=False):
        aio = self.env['sale.order']
        bdio = self.env['business.document.import']
        parsed_so = self.pre_process_parsed_so(parsed_so)
        (vals, import_config) = self._prepare_create_sale_order_vals(
            parsed_so, import_config=import_config)
        logger.debug('Sale Order vals for creation: %s', vals)
        sale_order = aio.create(vals)
        self.post_process_sale_order(parsed_so, sale_order, import_config)
        logger.info('Sale Order ID %d created', sale_order.id)
        bdio.post_create_or_update(parsed_so, sale_order)
        return sale_order

    @api.model
    def _prepare_global_adjustment_line(
            self, diff_amount, sale_order, import_config):
        ailo = self.env['sale.order.line']
        prec = sale_order.currency_id.rounding
        sol_vals = {
            'name': _('Adjustment'),
            'quantity': 1,
            'price_unit': diff_amount,
            }
        # no taxes nor product on such a global adjustment line
        if import_config['sale_order_line_method'] == 'nline_no_product':
            sol_vals['account_id'] = import_config['account'].id
        elif import_config['sale_order_line_method'] == 'nline_static_product':
            account = ailo.get_sale_order_line_account(
                sale_order.type, import_config['product'],
                sale_order.fiscal_position_id, sale_order.company_id)
            sol_vals['account_id'] = account.id
        elif import_config['sale_order_line_method'] == 'nline_auto_product':
            res_cmp = float_compare(diff_amount, 0, precision_rounding=prec)
            company = sale_order.company_id
            if res_cmp > 0:
                if not company.adjustment_debit_account_id:
                    raise UserError(_(
                        "You must configure the 'Adjustment Debit Account' "
                        "on the Accounting Configuration page."))
                sol_vals['account_id'] = company.adjustment_debit_account_id.id
            else:
                if not company.adjustment_credit_account_id:
                    raise UserError(_(
                        "You must configure the 'Adjustment Credit Account' "
                        "on the Accounting Configuration page."))
                sol_vals['account_id'] = company.adjustment_credit_account_id.id
        logger.debug("Prepared global ajustment Sale Order line %s", sol_vals)
        return sol_vals

    @api.model
    def post_process_sale_order(self, parsed_so, sale_order, import_config):
        if parsed_so.get('type') =='out_sale_order':
            return
        prec = sale_order.currency_id.rounding
        # If untaxed amount is wrong, create adjustment lines
        if (
                import_config['sale_order_line_method'].startswith('nline') and
                sale_order.order_line and
                float_compare(
                    parsed_so['amount_untaxed'], sale_order.amount_untaxed,
                    precision_rounding=prec)):
            # Try to find the line that has a problem
            # TODO : on Sale Order creation, the lines are in the same
            # order, but not on Sale Order update...
            for i in range(len(parsed_so['order_line'])):
                if 'price_subtotal' not in parsed_so['order_line'][i]:
                    continue
                iline = sale_order.order_line[i]
                odoo_subtotal = iline.price_subtotal
                parsed_subtotal = parsed_so['order_line'][i]['price_subtotal']
                if float_compare(
                        odoo_subtotal, parsed_subtotal,
                        precision_rounding=prec):
                    diff_amount = float_round(
                        parsed_subtotal - odoo_subtotal,
                        precision_rounding=prec)
                    logger.info(
                        'Price subtotal difference found on Sale Order line %d '
                        '(source:%s, odoo:%s, diff:%s).',
                        i + 1, parsed_subtotal, odoo_subtotal, diff_amount)
                    copy_dict = {
                        'name': _('Adjustment on %s') % iline.name,
                        'quantity': 1,
                        'price_unit': diff_amount,
                        }
                    if import_config['sale_order_line_method'] ==\
                            'nline_auto_product':
                        copy_dict['product_id'] = False
                    # Add the adjustment line
                    iline.copy(copy_dict)
                    logger.info('Adjustment Sale Order line created')

    @api.multi
    def update_sale_order_lines(self, parsed_so, sale_order, seller):
        chatter = parsed_so['chatter_msg']
        ailo = self.env['sale.order.line']
        dpo = self.env['decimal.precision']
        qty_prec = dpo.precision_get('Product Unit of Measure')
        existing_lines = []
        for eline in sale_order.order_line:
            price_unit = 0.0
            if not float_is_zero(
                    eline.quantity, precision_digits=qty_prec):
                price_unit = eline.price_subtotal / float(eline.quantity)
            existing_lines.append({
                'product': eline.product_id or False,
                'name': eline.name,
                'qty': eline.quantity,
                'uom': eline.uom_id,
                'line': eline,
                'price_unit': price_unit,
                })
        compare_res = self.env['business.document.import'].compare_lines(
            existing_lines, parsed_so['order_line'], chatter, seller=seller)
        if not compare_res:
            return
        for eline, cdict in list(compare_res['to_update'].items()):
            write_vals = {}
            if cdict.get('qty'):
                chatter.append(_(
                    "The quantity has been updated on the Sale Order line "
                    "with product '%s' from %s to %s %s") % (
                        eline.product_id.display_name,
                        cdict['qty'][0], cdict['qty'][1],
                        eline.uom_id.name))
                write_vals['quantity'] = cdict['qty'][1]
            if cdict.get('price_unit'):
                chatter.append(_(
                    "The unit price has been updated on the Sale Order "
                    "line with product '%s' from %s to %s %s") % (
                        eline.product_id.display_name,
                        eline.price_unit, cdict['price_unit'][1],  # TODO fix
                        sale_order.currency_id.name))
                write_vals['price_unit'] = cdict['price_unit'][1]
            if write_vals:
                eline.write(write_vals)
        if compare_res['to_remove']:
            to_remove_label = [
                '%s %s x %s' % (
                    l.quantity, l.uom_id.name, l.product_id.name)
                for l in compare_res['to_remove']]
            chatter.append(_(
                "%d Sale Order line(s) deleted: %s") % (
                    len(compare_res['to_remove']),
                    ', '.join(to_remove_label)))
            compare_res['to_remove'].unlink()
        if compare_res['to_add']:
            to_create_label = []
            for add in compare_res['to_add']:
                line_vals = self._prepare_create_sale_order_line(
                    add['product'], add['uom'], add['import_line'], sale_order)
                new_line = ailo.create(line_vals)
                to_create_label.append('%s %s x %s' % (
                    new_line.quantity,
                    new_line.uom_id.name,
                    new_line.name))
            chatter.append(_("%d new Sale Order line(s) created: %s") % (
                len(compare_res['to_add']), ', '.join(to_create_label)))
        sale_order.compute_taxes()
        return True

    @api.model
    def _prepare_create_sale_order_line(self, product, uom, import_line, sale_order):
        new_line = self.env['sale.order.line'].new({
            'order_id': sale_order.id,
            'qty': import_line['qty'],
            'product_id': product,
        })
        new_line._onchange_product_id()
        vals = {
            f: new_line._fields[f].convert_to_write(new_line[f], new_line)
            for f in new_line._cache
        }
        vals.update({
            'product_id': product.id,
            'price_unit': import_line.get('price_unit'),
            'quantity': import_line['qty'],
            'order_id': sale_order.id,
            })
        return vals

    @api.model
    def _prepare_update_sale_order_vals(self, parsed_so, sale_order):
        bdio = self.env['business.document.import']
        vals = {
            'reference': parsed_so.get('cus_po_num'),
            'date_order': parsed_so.get('date'),
        }
        if parsed_so.get('date_due'):
            vals['date_due'] = parsed_so['date_due']
        if parsed_so.get('iban'):
            company = sale_order.company_id
            partner_bank = bdio._match_partner_bank(
                sale_order.partner_id, parsed_so['iban'],
                parsed_so.get('bic'), parsed_so['chatter_msg'],
                create_if_not_found=company.sale_order_import_create_bank_account)
            if partner_bank:
                vals['partner_bank_id'] = partner_bank.id
        return vals

    @api.multi
    def update_sale_order(self):
        '''Called by the button of the wizard (step 'update-from-sale-order')'''
        self.ensure_one()
        iaao = self.env['ir.actions.act_window']
        bdio = self.env['business.document.import']
        sale_order = self.order_id
        if not sale_order:
            raise UserError(_(
                'You must select a supplier Sale Order or refund to update'))
        parsed_so = self.parse_sale_order(
            self.sale_order_file, self.sale_order_filename)
        if self.partner_id:
            # True if state='update' ; False when state='update-from-sale-order'
            parsed_so['partner']['recordset'] = self.partner_id
        partner = bdio._match_partner(
            parsed_so['partner'], parsed_so['chatter_msg'],
            partner_type='supplier')
        # partner = partner.commercial_partner_id
        if partner.id != sale_order.partner_id:
            raise UserError(_(
                "The customer of the imported Sale Order (%s) is different from "
                "the customer of the Sale Order to update (%s).") % (
                    partner.name,
                    sale_order.partner_id.name))
        if not self.import_config_id:
            raise UserError(_(
                "You must select an Sale Order Import Configuration."))
        import_config = self.import_config_id.convert_to_import_config()
        currency = bdio._match_currency(
            parsed_so.get('currency'), parsed_so['chatter_msg'])
        if currency != sale_order.currency_id:
            raise UserError(_(
                "The currency of the imported Sale Order (%s) is different from "
                "the currency of the existing Sale Order (%s)") % (
                currency.name, sale_order.currency_id.name))
        vals = self._prepare_update_sale_order_vals(parsed_so, sale_order)
        logger.debug('Updating customer Sale Order with vals=%s', vals)
        self.order_id.write(vals)
        if (
                parsed_so.get('order_line') and
                import_config['sale_order_line_method'] == 'nline_auto_product'):
            self.update_sale_order_lines(parsed_so, sale_order, partner)
        self.post_process_sale_order(parsed_so, sale_order, import_config)
        if import_config['account_analytic']:
            sale_order.order_line.write({
                'account_analytic_id': import_config['account_analytic'].id})
        bdio.post_create_or_update(parsed_so, sale_order)
        logger.info(
            'Supplier Sale Order ID %d updated via import of file %s',
            sale_order.id, self.sale_order_filename)
        sale_order.message_post(body=_(
            "This Sale Order has been updated automatically via the import "
            "of file %s") % self.sale_order_filename)
        action = iaao.for_xml_id('account', 'action_Sale Order_tree2')
        action.update({
            'view_mode': 'form,tree,calendar,graph',
            'views': False,
            'res_id': sale_order.id,
            })
        return action

    def xpath_to_dict_helper(self, xml_root, xpath_dict, namespaces):
        for key, value in xpath_dict.items():
            if isinstance(value, list):
                isdate = isfloat = False
                if 'date' in key:
                    isdate = True
                elif 'amount' in key:
                    isfloat = True
                xpath_dict[key] = self.multi_xpath_helper(
                    xml_root, value, namespaces, isdate=isdate,
                    isfloat=isfloat)
                if not xpath_dict[key]:
                    logger.debug('pb')
            elif isinstance(value, dict):
                xpath_dict[key] = self.xpath_to_dict_helper(
                    xml_root, value, namespaces)
        return xpath_dict
        # TODO: think about blocking required fields

    def multi_xpath_helper(
            self, xml_root, xpath_list, namespaces, isdate=False,
            isfloat=False):
        assert isinstance(xpath_list, list)
        for xpath in xpath_list:
            xpath_res = xml_root.xpath(xpath, namespaces=namespaces)
            if xpath_res and xpath_res[0].text:
                if isdate:
                    if (
                            xpath_res[0].attrib and
                            xpath_res[0].attrib.get('format') != '102'):
                        raise UserError(_(
                            "Only the date format 102 is supported "))
                    date_dt = datetime.strptime(xpath_res[0].text, '%Y%m%d')
                    date_str = fields.Date.to_string(date_dt)
                    return date_str
                elif isfloat:
                    res_float = float(xpath_res[0].text)
                    return res_float
                else:
                    return xpath_res[0].text
        return False

    def raw_multi_xpath_helper(self, xml_root, xpath_list, namespaces):
        for xpath in xpath_list:
            xpath_res = xml_root.xpath(xpath, namespaces=namespaces)
            if xpath_res:
                return xpath_res
        return []

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        logger.info(
            'New email received associated with sale.order.import: '
            'From: %s, Subject: %s, Date: %s, Message ID: %s. Executing '
            'with user %s ID %d',
            msg_dict.get('email_from'), msg_dict.get('subject'),
            msg_dict.get('date'), msg_dict.get('message_id'),
            self.env.user.name, self.env.user.id)
        # It seems that the "Odoo-way" to handle multi-company in E-mail
        # gateways is by using mail.aliases associated with users that
        # don't switch company (I haven't found any other way), which
        # is not convenient because you may have to create new users
        # for that purpose only. So I implemented my own mechanism,
        # based on the destination email address.
        # This method is called (indirectly) by the fetchmail cron which
        # is run by default as admin and retreive all incoming email in
        # all email accounts. We want to keep this default behavior,
        # and, in multi-company environnement, differentiate the company
        # per destination email address
        company_id = False
        all_companies = self.env['res.company'].search_read(
            [], ['sale_order_import_email'])
        if len(all_companies) > 1:  # multi-company setup
            for company in all_companies:
                if company['sale_order_import_email']:
                    company_dest_email = company['sale_order_import_email']\
                        .strip()
                    if (
                            company_dest_email in msg_dict.get('to', '') or
                            company_dest_email in msg_dict.get('cc', '')):
                        company_id = company['id']
                        logger.info(
                            'Matched with %s: importing Sale Orders in company '
                            'ID %d', company_dest_email, company_id)
                        break
            if not company_id:
                logger.error(
                    'Sale Order import mail gateway in multi-company setup: '
                    'Sale Order_import_email of the companies of this DB was '
                    'not found as destination of this email (to: %s, cc: %s). '
                    'Ignoring this email.',
                    msg_dict['email_to'], msg_dict['cc'])
                return
        else:  # mono-company setup
            company_id = all_companies[0]['id']

        self = self.with_context(force_company=company_id)
        aiico = self.env['sale.order.import.config']
        bdio = self.env['business.document.import']
        i = 0
        if msg_dict.get('attachments'):
            i += 1
            for attach in msg_dict['attachments']:
                logger.info(
                    'Attachment %d: %s. Trying to import it as an Sale Order',
                    i, attach.fname)
                parsed_so = self.parse_sale_order(
                    base64.b64encode(attach.content), attach.fname)
                partner = bdio._match_partner(
                    parsed_so['partner'], parsed_so['chatter_msg'])

                existing_inv = self.sale_order_already_exists(partner, parsed_so)
                if existing_inv:
                    logger.warning(
                        "Mail import: this supplier Sale Order already exists "
                        "in Odoo (ID %d number %s supplier number %s)",
                        existing_inv.id, existing_inv.number,
                        parsed_so.get('sale_order_number'))
                    continue
                import_configs = aiico.search([
                    ('partner_id', '=', partner.id),
                    ('company_id', '=', company_id)])
                if not import_configs:
                    logger.warning(
                        "Mail import: missing Sale Order Import Configuration "
                        "for partner '%s'.", partner.display_name)
                    continue
                elif len(import_configs) == 1:
                    import_config = import_configs.convert_to_import_config()
                else:
                    logger.info(
                        "There are %d Sale Order import configs for partner %s. "
                        "Using the first one '%s''", len(import_configs),
                        partner.display_name, import_configs[0].name)
                    import_config =\
                        import_configs[0].convert_to_import_config()
                sale_order = self.create_sale_order(parsed_so, import_config)
                logger.info('Sale Order ID %d created from email', sale_order.id)
                sale_order.message_post(body=_(
                    "Sale Order successfully imported from email sent by "
                    "<b>%s</b> on %s with subject <i>%s</i>.") % (
                        msg_dict.get('email_from'), msg_dict.get('date'),
                        msg_dict.get('subject')))
        else:
            logger.info('The email has no attachments, skipped.')
