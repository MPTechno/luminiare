from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountInvoice(models.Model):
    _inherit = "account.invoice"


    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_discount = self.amount_tax = self.amount_commission = 0.0
        if self.discount_type == 'amount':
            self.amount_discount = self.discount_rate
            self.amount_tax = self.tax_rate
        if self.discount_type == 'percent':
            self.amount_discount = (self.amount_untaxed * self.discount_rate ) / 100
            self.amount_tax = (((self.amount_untaxed) * self.tax_rate)/100)
        if self.commission_type == 'amount':
            self.amount_commission = self.commission_rate
        if self.commission_type == 'percent':
            self.amount_commission = (((self.amount_untaxed - self.amount_discount)*self.commission_rate)/100)

        self.amount_total = ((self.amount_untaxed - self.amount_discount) + self.amount_tax)
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign


    commission_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')], string='Commission Type',
                                     readonly=True, states={'draft': [('readonly', False)]}, default='percent')
    commission_rate = fields.Float('Commission Amount', digits=(16, 2), readonly=True, states={'draft': [('readonly', False)]})
    amount_commission = fields.Monetary(string='Commission', store=True, readonly=True, compute='_compute_amount',
                                      track_visibility='always')

    @api.model
    def invoice_line_move_line_get(self):
        res = []
        for line in self.invoice_line_ids:
            if line.quantity==0:
                continue
            tax_ids = []
            for tax in line.invoice_line_tax_ids:
                tax_ids.append((4, tax.id, None))
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        tax_ids.append((4, child.id, None))
            analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
            price = line.price_subtotal
            if self.amount_discount:
                price = line.price_subtotal - self.amount_discount
            move_line_dict = {
                'invl_id': line.id,
                'type': 'src',
                'name': line.name.split('\n')[0][:64],
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'price': price,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,
                'account_analytic_id': line.account_analytic_id.id,
                'tax_ids': tax_ids,
                'invoice_id': self.id,
                'analytic_tag_ids': analytic_tag_ids
            }
            if line['account_analytic_id']:
                move_line_dict['analytic_line_ids'] = [(0, 0, line._get_analytic_line())]
            res.append(move_line_dict)
        return res

    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        total = 0
        total_currency = 0
        for line in invoice_move_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(date=self.date or self.date_invoice or fields.Date.context_today(self))
                if not (line.get('currency_id') and line.get('amount_currency')):
                    line['currency_id'] = currency.id
                    line['amount_currency'] = currency.round(line['price'])
                    line['price'] = currency.compute(line['price'], company_currency)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = self.currency_id.round(line['price'])
            if self.type in ('out_invoice', 'in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, invoice_move_lines

    def _prepare_tax_line_vals(self, line, tax):
        """ Prepare values to create an account.invoice.tax line

        The line parameter is an account.invoice.line, and the
        tax parameter is the output of account.tax.compute_all().
        """
        vals = {
            'invoice_id': self.id,
            'name': tax['name'],
            'tax_id': tax['id'],
            'amount': self.amount_tax,
            'base': tax['base'],
            'manual': False,
            'sequence': tax['sequence'],
            'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
            'account_id': self.type in ('out_invoice', 'in_invoice') and (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
        }

        # If the taxes generate moves on the same financial account as the invoice line,
        # propagate the analytic account from the invoice line to the tax line.
        # This is necessary in situations were (part of) the taxes cannot be reclaimed,
        # to ensure the tax move is allocated to the proper analytic account.
        if not vals.get('account_analytic_id') and line.account_analytic_id and vals['account_id'] == line.account_id.id:
            vals['account_analytic_id'] = line.account_analytic_id.id

        return vals

    @api.multi
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft']):
            raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        to_open_invoices.action_create_commissin_move()
        return to_open_invoices.invoice_validate()

    def action_create_commissin_move(self):
        if self.journal_id:
            journal = self.journal_id
            name = journal.with_context(ir_sequence_date=fields.Date.today()).sequence_id.next_by_id()
            referral_fee_account_obj = self.env['ir.model.data'].get_object('solum_invoice', 'luminiare_referal_fee_account')
            print "\n\n=referral_fee_account_obj",referral_fee_account_obj
            #other_payable_account_obj = self.env['ir.model.data'].get_object('l10n_sg', 'account_account_778')
            #print "\n\n=other_payable_account_obj",other_payable_account_obj
            other_payable_account_obj = self.env['account.account'].search([('code','=','202002')])
            line = [(0, 0, {'analytic_account_id': False, 'tax_ids': False, 'name': 'Referral Fees', 'analytic_tag_ids': [], 'product_uom_id': False, 'invoice_id': self.id, 'analytic_line_ids': [], 'tax_line_id': False, 'currency_id': False, 'credit': self.amount_commission, 'product_id': False, 'date_maturity': False, 'debit': False, 'amount_currency': 0, 'quantity': 1.0, 'partner_id': self.partner_id.id, 'account_id': referral_fee_account_obj.id}),
                    (0, 0, {'analytic_account_id': False, 'tax_ids': False, 'name': '/', 'analytic_tag_ids': False, 'product_uom_id': False, 'invoice_id': self.id, 'analytic_line_ids': [], 'tax_line_id': False, 'currency_id': False, 'credit': False, 'product_id': False, 'date_maturity': False, 'debit': self.amount_commission, 'amount_currency': 0, 'quantity': 1.0, 'partner_id': self.partner_id.id, 'account_id': other_payable_account_obj.id})]
            move_vals = {
                'name': name,
                'date': fields.Date.today(),
                'ref': self.number or '',
                'company_id': self.company_id.id,
                'journal_id': journal.id,
                'line_ids': line,
            }
            move = self.env['account.move'].create(move_vals)
            move.post()
            return True
