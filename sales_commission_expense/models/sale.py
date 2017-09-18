# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:

            amount_untaxed = amount_tax = amount_discount = amount_commission = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                if order.discount_type == 'percent':
                    amount_discount = (amount_untaxed * order.discount_rate) / 100
                    amount_tax = (((amount_untaxed) * order.tax_rate )/100)
            	if order.discount_type == 'amount':
            	    amount_discount = order.discount_rate
            	    amount_tax = order.tax_rate
                if order.commission_type == 'percent':
                    amount_commission = (((amount_untaxed -amount_discount) * order.commission_rate)/100)
            	if order.commission_type == 'amount':
            	    amount_commission = order.commission_rate
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_discount': order.pricelist_id.currency_id.round(amount_discount),
                'amount_commission': order.pricelist_id.currency_id.round(amount_commission),
                'amount_total': (((amount_untaxed - amount_discount) - amount_commission)  + amount_tax)
            })

    @api.onchange('discount_type', 'discount_rate','tax_rate','commission_rate','commission_type')
    def supply_rate(self):
        amount_total = amount_discount = amount_tax = amount_commission = 0.0
        for order in self:
            if order.discount_type == 'percent':
                order.amount_discount = amount_discount = ((order.amount_untaxed * self.discount_rate)/100)
                order.amount_tax = amount_tax = (((order.amount_untaxed) * self.tax_rate) / 100)
                amount_total = (order.amount_untaxed) - self.amount_discount
            if order.discount_type == 'amount':
                order.amount_discount = amount_discount = self.discount_rate
                order.amount_tax = amount_tax = self.tax_rate
                amount_total = (order.amount_untaxed) - self.amount_discount
            if order.commission_type == 'percent':
                order.amount_commission = amount_commission = ((amount_total * self.commission_rate)/100)
            if order.commission_type == 'amount':
                order.amount_commission = amount_commission = self.commission_rate
            amount_total = (order.amount_untaxed + order.amount_tax ) - self.amount_discount
            order.amount_total = amount_total - order.amount_commission

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}
        references = {}
        for order in self:
            group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)
            for line in order.order_line.sorted(key=lambda l: l.qty_to_invoice < 0):
                if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()
                    invoice = inv_obj.create(inv_data)
                    references[invoice] = order
                    invoices[group_key] = invoice
                elif group_key in invoices:
                    vals = {}
                    if order.name not in invoices[group_key].origin.split(', '):
                        vals['origin'] = invoices[group_key].origin + ', ' + order.name
                    if order.client_order_ref and order.client_order_ref not in invoices[group_key].name.split(', ') and order.client_order_ref != invoices[group_key].name:
                        vals['name'] = invoices[group_key].name + ', ' + order.client_order_ref
                    invoices[group_key].write(vals)
                if line.qty_to_invoice > 0:
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
                elif line.qty_to_invoice < 0 and final:
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
            if references.get(invoices.get(group_key)):
                if order not in references[invoices[group_key]]:
                    references[invoice] = references[invoice] | order

        if not invoices:
            raise UserError(_('There is no invoicable line.'))

        for invoice in invoices.values():
            if not invoice.invoice_line_ids:
                raise UserError(_('There is no invoicable line.'))
            # If invoice is negative, do a refund invoice instead
            if invoice.amount_untaxed < 0:
                invoice.type = 'out_refund'
                for line in invoice.invoice_line_ids:
                    line.quantity = -line.quantity
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            invoice.message_post_with_view('mail.message_origin_link',
                values={'self': invoice, 'origin': references[invoice]},
                subtype_id=self.env.ref('mail.mt_note').id)
        discount_limit = self.env.ref('sale_discount_total.discount_limit_verification').value
        if invoice:
            #if sale_order_ids.amount_discount > 0:
            discount_rate = ((self.amount_discount*100)/ self.amount_untaxed)
            if float(discount_rate) <= float(discount_limit):
                invoice.action_invoice_open()
        return [inv.id for inv in invoices.values()]