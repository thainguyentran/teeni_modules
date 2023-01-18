# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models, _
from odoo.tools import email_re, email_split, email_escape_char, float_is_zero, float_compare, \
    pycompat, date_utils
from odoo.tools.misc import formatLang

from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class Accounts(models.Model):
    _inherit = "account.invoice"

    @api.model
    def invoice_line_move_line_get(self):
        res = []
        dis_per_line = 0
        tot_line = len(self.invoice_line_ids)
        if self.get_invoice_discount_in_base_currency():
            dis_per_line = (self.invoice_discount_amount / tot_line) * 2
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue
            if line.quantity == 0:
                continue
            tax_ids = []
            for tax in line.invoice_line_tax_ids:
                tax_ids.append((4, tax.id, None))
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        tax_ids.append((4, child.id, None))
            analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
            print("SubTotal", line.price_subtotal, dis_per_line)
            move_line_dict = {
                'invl_id': line.id,
                'type': 'src',
                'name': line.name,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'price': line.price_subtotal - dis_per_line,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,
                'account_analytic_id': line.account_analytic_id.id,
                'analytic_tag_ids': analytic_tag_ids,
                'tax_ids': tax_ids,
                'invoice_id': self.id,
            }
            res.append(move_line_dict)
        return res

    def get_invoice_discount_in_base_currency(self):
        if self.invoice_discount_amount and self.currency_id:
            cr = self.currency_id.rate
            return self.invoice_discount_amount / cr
        elif self.invoice_discount_amount:
            return self.invoice_discount_amount
        else:
            return 0

    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids.filtered(lambda line: line.account_id):
                raise UserError(_('Please add at least one invoice line.'))
            if inv.move_id:
                continue


            if not inv.date_invoice:
                inv.write({'date_invoice': fields.Date.context_today(self)})
            if not inv.date_due:
                inv.write({'date_due': inv.date_invoice})
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            print("I!", iml)
            iml += inv.tax_line_move_line_get()


            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.compute_invoice_totals(company_currency, iml)

            name = inv.name or ''
            if inv.payment_term_id:
                totlines = inv.payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)[0]
                res_amount_currency = total_currency
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency._convert(t[1], inv.currency_id, inv.company_id, inv._get_currency_rate_date() or fields.Date.today())
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    print("ICUR ", amount_currency,self.get_invoice_discount_in_base_currency, self.invoice_discount_amount)
                    if self.invoice_discount_amount:
                        amount_currency += self.invoice_discount_amount

                    print("ICR After", amount_currency)


                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1]+self.get_invoice_discount_in_base_currency(),
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
                    print("If Total", t[1], self.get_invoice_discount_in_base_currency(), iml)
            else:
                print("Else Total", total, self.get_invoice_discount_in_base_currency())
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total+self.get_invoice_discount_in_base_currency(),
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            print("IML",total, iml)
            if self.invoice_discount_amount:
                iml.append({
                    'type': 'src',
                    'name': name,
                    'price': -self.get_invoice_discount_in_base_currency(),
                    'account_id': inv.discount_account.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and self.invoice_discount_amount,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })

            print("IML 2", iml)
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            print("Line 1", line)
            line = inv.group_lines(iml, line)
            print("Line 2", line)
            line = inv.finalize_invoice_move_lines(line)
            print("Line 3", line)
            date = inv.date or inv.date_invoice

            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': inv.journal_id.id,
                'date': date,
                'narration': inv.comment,
            }
            move = account_move.create(move_vals)
            # Pass invoice in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:

            move.post(invoice = inv)
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.write(vals)
        return True


