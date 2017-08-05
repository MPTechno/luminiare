from odoo import fields, models, exceptions, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError,Warning
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
                amount_tax += line.price_tax
                amount_discount += (line.product_uom_qty * line.price_unit * line.discount)/100
                if order.discount_type == 'percent':
                    amount_discount = (amount_untaxed * order.discount_rate) / 100
            	if order.discount_type == 'amount':
            	    amount_discount = order.discount_rate
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_discount': order.pricelist_id.currency_id.round(amount_discount),
                'amount_total': amount_untaxed -amount_discount + amount_tax ,
            })

    discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')], string='Discount/Tax Type',
                                     readonly=True,states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                     default='percent')
    discount_rate = fields.Float('Discount Rate', digits_compute=dp.get_precision('Account'),
                                 readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all',
                                 track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all',
                                   track_visibility='always')
    amount_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='_amount_all',
                                      digits_compute=dp.get_precision('Account'), track_visibility='always')
                                      

    @api.onchange('discount_type', 'discount_rate')
    def supply_rate(self):
        for order in self:
            if order.discount_type == 'percent':
                order.amount_discount = ((order.amount_untaxed * self.discount_rate)/100)
                order.amount_total = (order.amount_untaxed + order.amount_tax ) - self.amount_discount
            if order.discount_type == 'amount':
                order.amount_discount = self.discount_rate
                order.amount_total = (order.amount_untaxed + order.amount_tax ) - self.amount_discount
                
    @api.multi
    def _prepare_invoice(self,):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate
        })
        return invoice_vals

    @api.multi
    def get_warning_alert(self,message):
        if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
            self.action_done()
        imd = self.env['ir.model.data']
        view = imd.get_object_reference('sale_discount_total','view_warning_message_wizard')
        view_id = view and view[1] or False
        context = dict(self._context)
        context.update({
            'default_message': message,
        })
        vals =  {
            'name': _('Warning'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'warning.message',
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
		}
        return vals
        
    
    @api.multi
    def action_confirm(self):
        discount_limit = self.env.ref('sale_discount_total.discount_limit_verification').value
        warning_mess = {}
        for order in self:
            if order.amount_discount > 0:
                discount_rate = ((order.amount_discount*100)/ order.amount_untaxed)
                if float(discount_rate) > float(discount_limit):
                     raise UserError(_('You will not apply discount more then %s%s !') % (discount_limit,'%'))
            order.state = 'sale'
            order.confirmation_date = fields.Datetime.now()
            if self.env.context.get('send_email'):
                self.force_quotation_send()
            order.order_line._action_procurement_create()
            message = ''
            for order_line in order.order_line:
                if order_line.product_id.is_pack:
                    if order_line.product_id.wk_product_pack:
                        for product_pack in order_line.product_id.wk_product_pack:
                            outgoing_qty = product_pack.product_name.outgoing_qty - order_line.product_uom_qty
                            available_qty = product_pack.product_name.qty_available - outgoing_qty
                            if available_qty < order_line.product_uom_qty:
                                lacking_qty = order_line.product_uom_qty - available_qty
                                message += _('You plan to sell %s of %s qty but you have only %s qty available! The lacking quantity is %s. \n')%\
                                    (str(product_pack.product_name.name), order_line.product_uom_qty, available_qty, lacking_qty)
                            
                else:    	
                    outgoing_qty = order_line.product_id.outgoing_qty - order_line.product_uom_qty
                    available_qty = order_line.product_id.qty_available - outgoing_qty
                    if available_qty < order_line.product_uom_qty:
                        lacking_qty = order_line.product_uom_qty - available_qty
                        message += _('You plan to sell %s of %s qty but you have only %s qty available! The lacking quantity is %s. \n')%\
                                    (str(order_line.product_id.name), order_line.product_uom_qty, available_qty, lacking_qty)
            if message:
                return self.get_warning_alert(message)
        return True
    
    @api.multi
    def button_dummy(self):
        self.supply_rate()
        return True

class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.multi
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id
        if not currency:
            currency = company_id.currency_id
        taxes = []
        prec = currency.decimal_places
        round_tax = False if company_id.tax_calculation_rounding_method == 'round_globally' else True
        round_total = True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])
            round_total = bool(self.env.context['round'])

        if not round_tax:
            prec += 5
        total_excluded = total_included = base = (price_unit * quantity)

        for tax in self.sorted(key=lambda r: r.sequence):
            if tax.amount_type == 'group':
                ret = tax.children_tax_ids.compute_all(price_unit, currency, quantity, product, partner)
                total_excluded = ret['total_excluded']
                base = ret['base']
                total_included = ret['total_included']
                tax_amount = total_included - total_excluded
                taxes += ret['taxes']
                continue

            tax_amount = tax._compute_amount(base, price_unit, quantity, product, partner)
            if not round_tax:
                tax_amount = round(tax_amount, prec)
            else:
                tax_amount = currency.round(tax_amount)

            if tax.price_include:
                total_excluded -= tax_amount
                base -= tax_amount
            else:
                total_included += tax_amount
            
            tax_base = base
            
            if tax.include_base_amount:
                base += tax_amount

            taxes.append({
                'id': tax.id,
                'name': tax.with_context(**{'lang': partner.lang} if partner else {}).name,
                'amount': tax_amount,
                'sequence': tax.sequence,
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
                'analytic': tax.analytic,
                'base': tax_base,
            })
        return {
            'taxes': sorted(taxes, key=lambda k: k['sequence']),
            'total_excluded': total_excluded,
            'total_included': total_included,
            'base': base,
        }

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0)
