from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0,limit=None, order=None):
        result = super(AccountInvoice, self).search_read(domain, fields, offset, limit, order)
        for res in result:
		    if res.has_key('discount_type'):
		        if res['discount_type'] == 'amount':
		            amount_untaxed = res['amount_untaxed']
		            amount_discount = res['discount_rate']
		            amount_tax = res['tax_rate']
		            amount_total = amount_untaxed - amount_discount + amount_tax
		            res.update({
		            	'amount_discount':amount_discount,
		            	'amount_tax': amount_tax,
		            	'amount_total': amount_total,
		            	'residual':amount_total
		            })
		        if res['discount_type'] == 'percent':
		            amount_untaxed = res['amount_untaxed']
		            amount_discount = (amount_untaxed * res['discount_rate'])/100
		            amount_tax = (((amount_untaxed - amount_discount) * res['tax_rate'])/100)
		            amount_total = amount_untaxed - amount_discount + amount_tax
		            res.update({
		            	'amount_discount':amount_discount,
		            	'amount_tax': amount_tax,
		            	'amount_total': amount_total,
		            	'residual':amount_total
		            })   
        return result
    
    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_discount = self.amount_tax = 0.0
        if self.discount_type == 'amount':
            self.amount_discount = self.discount_rate
            self.amount_tax = self.tax_rate
        
        if self.discount_type == 'percent':
            self.amount_discount = (self.amount_untaxed * self.discount_rate ) / 100
            self.amount_tax = (((self.amount_untaxed - self.amount_discount) * self.tax_rate)/100)
        
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


    tax_rate = fields.Float('Tax Amount', digits=(16, 2), readonly=True, states={'draft': [('readonly', False)]})
    
    
    @api.onchange('discount_type', 'discount_rate', 'tax_rate')
    def supply_rate(self):
        for inv in self:
            if inv.discount_type == 'percent':
                inv.amount_discount = ((inv.amount_untaxed * self.discount_rate)/100)
                inv.amount_tax = (((inv.amount_untaxed - inv.amount_discount) * self.tax_rate) /100)
                inv.amount_total = (inv.amount_untaxed + inv.amount_tax ) - self.amount_discount
            if inv.discount_type == 'amount':
                inv.amount_discount = self.discount_rate
                inv.amount_tax = self.tax_rate
                inv.amount_total = (inv.amount_untaxed + inv.amount_tax ) - self.amount_discount

    @api.multi
    def button_dummy(self):
        self.supply_rate()
        return True
