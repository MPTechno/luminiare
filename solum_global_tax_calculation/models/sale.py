from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                if order.discount_type == 'percent':
                    amount_discount = (amount_untaxed * order.discount_rate) / 100
                    amount_tax = (((amount_untaxed - amount_discount) * order.tax_rate )/100) 
            	if order.discount_type == 'amount':
            	    amount_discount = order.discount_rate
            	    amount_tax = order.tax_rate
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_discount': order.pricelist_id.currency_id.round(amount_discount),
                'amount_total': amount_untaxed -amount_discount + amount_tax ,
            })
    
    
    @api.model
    @api.depends('quote_type')
    def _default_tax_rate(self):
        tax_rate = 0.00
        if self._context.has_key('default_quote_type') and self._context.get('default_quote_type') == 'idesign':
            tax_rate = 7.0
        return tax_rate
    
    
    tax_rate = fields.Float('Tax Rate', digits_compute=dp.get_precision('Account'), default=_default_tax_rate,
                                 readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all',
                                 track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all',
                                   track_visibility='always')
    amount_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='_amount_all',
                                      digits_compute=dp.get_precision('Account'), track_visibility='always')
                                      
                                      
    @api.onchange('discount_type', 'discount_rate','tax_rate')
    def supply_rate(self):
        for order in self:
            if order.discount_type == 'percent':
                order.amount_discount = ((order.amount_untaxed * self.discount_rate)/100)
                order.amount_tax = (((order.amount_untaxed - order.amount_discount) * self.tax_rate) / 100)
                order.amount_total = (order.amount_untaxed + order.amount_tax ) - self.amount_discount
            if order.discount_type == 'amount':
                order.amount_discount = self.discount_rate
                order.amount_tax = self.tax_rate
                order.amount_total = (order.amount_untaxed + order.amount_tax ) - self.amount_discount
                
    @api.multi
    def _prepare_invoice(self,):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate,
            'tax_rate': self.tax_rate
        })
        return invoice_vals

    @api.multi
    def button_dummy(self):
        self.supply_rate()
        return True
