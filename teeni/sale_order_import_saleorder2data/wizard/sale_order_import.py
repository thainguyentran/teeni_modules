from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import os
from tempfile import mkstemp
import logging
logger = logging.getLogger(__name__)

try:
    from invoice2data.main import extract_data
    from invoice2data.extract.loader import read_templates
    from invoice2data.main import logger as loggeri2data
except ImportError:
    logger.debug('Cannot import invoice2data')


class SaleOrderImport(models.TransientModel):
    _inherit = 'sale.order.import'

    @api.model
    def fallback_parse_pdf_sale_order(self, file_data):
        '''This method must be inherited by additional modules with
        the same kind of logic as the account_bank_statement_import_*
        modules'''
        return self.invoice2data_parse_sale_order(file_data)

    @api.model
    def invoice2data_parse_sale_order(self, file_data):
        logger.info('Trying to analyze PDF sale order with invoice2data lib')
        fd, file_name = mkstemp()
        try:
            os.write(fd, file_data)
        finally:
            os.close(fd)
        # Transfer log level of Odoo to invoice2data
        loggeri2data.setLevel(logger.getEffectiveLevel())
        local_templates_dir = tools.config.get(
            'invoice2data_templates_dir', False)
        logger.debug(
            'invoice2data local_templates_dir=%s', local_templates_dir)
        templates = []
        if local_templates_dir and os.path.isdir(local_templates_dir):
            templates += read_templates(local_templates_dir)
        exclude_built_in_templates = tools.config.get(
            'invoice2data_exclude_built_in_templates', False)
        if not exclude_built_in_templates:
            templates += read_templates()
        logger.debug(
            'Calling invoice2data.extract_data with templates=%s',
            templates)
        try:
            invoice2data_res = extract_data(file_name, templates=templates)
        except Exception as e:
            raise UserError(_(
                "PDF Invoice parsing failed. Error message: %s") % e)
        if not invoice2data_res:
            raise UserError(_(
                "This PDF invoice doesn't match a known template of "
                "the invoice2data lib."))
        logger.info(
            'Result of invoice2data PDF extraction: %s', invoice2data_res)
        return self.invoice2data_to_parsed_so(invoice2data_res)

    @api.model
    def invoice2data_to_parsed_so(self, invoice2data_res):
        if invoice2data_res.get('partner_name'):
            parsed_so = {
                'partner': {
                    'vat': invoice2data_res.get('vat'),
                    'name': invoice2data_res.get('partner_name'),
                    'email': invoice2data_res.get('partner_email'),
                    'website': invoice2data_res.get('partner_website'),
                    'siren': invoice2data_res.get('siren'),
                    },
                'currency': {
                    'iso': invoice2data_res.get('currency'),
                    },
                'amount_total': invoice2data_res.get('amount'),
                'date': invoice2data_res.get('date'),
                'date_due': invoice2data_res.get('date_due'),
                'date_start': invoice2data_res.get('date_start'),
                'date_end': invoice2data_res.get('date_end'),
                'cus_po_num': invoice2data_res.get('cus_po_num'),
                'store_code': invoice2data_res.get('store_code'),
                'order_line': [],
                }
        else:
            parsed_so = {
                'partner': {
                    'vat': invoice2data_res.get('vat'),
                    'name': invoice2data_res.get('issuer'),
                    'email': invoice2data_res.get('partner_email'),
                    'website': invoice2data_res.get('partner_website'),
                    'siren': invoice2data_res.get('siren'),
                    },
                'currency': {
                    'iso': invoice2data_res.get('currency'),
                    },
                'amount_total': invoice2data_res.get('amount'),
                'date': invoice2data_res.get('date'),
                'date_due': invoice2data_res.get('date_due'),
                'date_start': invoice2data_res.get('date_start'),
                'date_end': invoice2data_res.get('date_end'),
                'cus_po_num': invoice2data_res.get('cus_po_num'),
                'store_code': invoice2data_res.get('store_code'),
                'order_line': [],
                }
        for field in ['cus_po_num', 'description']:
            if isinstance(invoice2data_res.get(field), list):
                parsed_so[field] = ' '.join(invoice2data_res[field])
            else:
                parsed_so[field] = invoice2data_res.get(field)
        if 'lines' in invoice2data_res:
            parsed_so['order_line'] = invoice2data_res['lines']
        if 'amount_untaxed' in invoice2data_res:
            parsed_so['amount_untaxed'] = invoice2data_res['amount_untaxed']
        if 'amount_tax' in invoice2data_res:
            parsed_so['amount_tax'] = invoice2data_res['amount_tax']
        for key, value in parsed_so.items():
            if key.startswith('date') and parsed_so[key]:
                parsed_so[key] = fields.Date.to_string(parsed_so[key])
        logger.info(
            'Result of parsed_so: %s', parsed_so)
        return parsed_so
