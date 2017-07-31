from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = sum(line.amount for line in self.tax_line_ids)
        self.amount_discount = sum((line.quantity * line.price_unit * line.discount)/100 for line in self.invoice_line_ids)
        if self.discount_type == 'amount':
            self.amount_discount = self.discount_rate
        if self.discount_type == 'percent':
            self.amount_discount = (self.amount_untaxed * self.discount_rate ) / 100
        
        self.amount_total = self.amount_untaxed - self.amount_discount + self.amount_tax
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

    discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')], string='Discount/Tax Type',
                                     readonly=True, states={'draft': [('readonly', False)]}, default='percent')
    discount_rate = fields.Float('Discount Amount', digits=(16, 2), readonly=True, states={'draft': [('readonly', False)]})
    amount_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='_compute_amount',
                                      track_visibility='always')

    @api.onchange('discount_type', 'discount_rate')
    def supply_rate(self):
        for inv in self:
            if inv.discount_type == 'percent':
                inv.amount_discount = ((inv.amount_untaxed * self.discount_rate)/100)
                inv.amount_total = (inv.amount_untaxed + inv.amount_tax ) - self.amount_discount
            if inv.discount_type == 'amount':
                inv.amount_discount = self.discount_rate
                inv.amount_total = (inv.amount_untaxed + inv.amount_tax ) - self.amount_discount

    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        total = 0
        total_currency = 0
        for line in invoice_move_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(date=self.date_invoice or fields.Date.context_today(self))
                line['currency_id'] = currency.id
                line['amount_currency'] = currency.round(line['price'])
                line['price'] = currency.compute(line['price'], company_currency)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = line['price']
            if self.type in ('out_invoice', 'in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, invoice_move_lines

    @api.multi
    def button_dummy(self):
        self.supply_rate()
        return True

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"
    
    @api.model
    def create(self, vals):
        discount_limit = self.env.ref('sale_discount_total.discount_limit_verification').value
        invoice_line_obj = super(AccountInvoiceLine, self).create(vals)
        sale_order_pool = self.env['sale.order']
        if invoice_line_obj.invoice_id.origin:
            sale_order_ids = sale_order_pool.search([('name','=',invoice_line_obj.invoice_id.origin)])
            if sale_order_ids:
                if sale_order_ids.amount_discount > 0:
                    discount_rate = ((sale_order_ids.amount_discount*100)/ sale_order_ids.amount_untaxed)
                    if float(discount_rate) <= float(discount_limit):
                        invoice_line_obj.invoice_id.action_invoice_open()
        return invoice_line_obj
    
    discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0)
