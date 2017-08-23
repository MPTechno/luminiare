from itertools import groupby
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
import odoo.addons.decimal_precision as dp

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        res = {}
        account = self.product_id.property_account_income_id or self.product_id.categ_id.property_account_income_categ_id
        if not account:
            raise UserError(_('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (self.product_id.name, self.product_id.id, self.product_id.categ_id.name))

        fpos = self.order_id.fiscal_position_id or self.order_id.partner_id.property_account_position_id
        if fpos:
            account = fpos.map_account(account)

        res = {
            'name': self.name,
            'sequence': self.sequence,
            'origin': self.order_id.name,
            'account_id': account.id,
            'price_unit': self.price_unit,
            'quantity': qty,
            'discount': self.discount,
            'product_location_id': self.product_location_id and self.product_location_id.id or False,
            'length': self.length ,
            'colour_id': self.colour_id and self.colour_id.id and False ,
            'area_id': self.area_id and self.area_id.id or False,
            'uom_id': self.product_uom.id,
            'product_id': self.product_id.id or False,
            'layout_category_id': self.layout_category_id and self.layout_category_id.id or False,
            'product_id': self.product_id.id or False,
            'invoice_line_tax_ids': [(6, 0, self.tax_id.ids)],
            'account_analytic_id': self.order_id.project_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
        }
        return res

class SalesOrders(models.Model):
    _inherit = 'sale.order'
    
    
    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))
        invoice_vals = {
            'name': self.client_order_ref or '',
            'origin': self.name,
            'type': 'out_invoice',
            'account_id': self.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'journal_id': journal_id,
            'currency_id': self.pricelist_id.currency_id.id,
            'comment': self.note,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'inv_type':self.quote_type,
            'attention': self.attention,
            'payment_term_text': self.payment_term_text,
            'reference_no': self.reference_no,
            'sale_project_id':self.sale_project_id and self.sale_project_id.id or False,
        }
        return invoice_vals
    
    
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
                    inv_remarks_obj = self.env['invoice.remarks']
                    if order.remarks_ids:
                        for remarks in order.remarks_ids:
        	                invoice_remarks_vals = {
        	   	                'name': remarks.name and remarks.name.id or False,
        	   	                'invoice_id': invoice and invoice.id or False
        	                }
        	                inv_remarks_obj.create(invoice_remarks_vals)
                    references[invoice] = order
                    invoices[group_key] = invoice
                elif group_key in invoices:
                    vals = {}
                    if order.name not in invoices[group_key].origin.split(', '):
                        vals['origin'] = invoices[group_key].origin + ', ' + order.name
                    if order.client_order_ref and order.client_order_ref not in invoices[group_key].name.split(', '):
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
        return [inv.id for inv in invoices.values()]
    
    @api.multi
    def action_view_invoice(self):
        invoice_ids = self.mapped('invoice_ids')
        imd = self.env['ir.model.data']
        if self.quote_type == 'led_strip':
            action = imd.xmlid_to_object('solum_invoice.action_led_strip_invoices')
            list_view_id = imd.xmlid_to_res_id('account.invoice_tree')
            form_view_id = imd.xmlid_to_res_id('solum_invoice.led_strip_invoice_form')
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
                'target': action.target,
                'context': action.context,
                'res_model': action.res_model,
            }
            if len(invoice_ids) > 1:
                result['domain'] = "[('id','in',%s)]" % invoice_ids.ids
            elif len(invoice_ids) == 1:
                result['views'] = [(form_view_id, 'form')]
                result['res_id'] = invoice_ids.ids[0]
            else:
                result = {'type': 'ir.actions.act_window_close'}
            return result
        if self.quote_type == 'led_attach':
            action = imd.xmlid_to_object('solum_invoice.action_led_attach_invoices')
            list_view_id = imd.xmlid_to_res_id('account.invoice_tree')
            form_view_id = imd.xmlid_to_res_id('solum_invoice.led_attachment_invoice_form')
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
                'target': action.target,
                'context': action.context,
                'res_model': action.res_model,
            }
            if len(invoice_ids) > 1:
                result['domain'] = "[('id','in',%s)]" % invoice_ids.ids
            elif len(invoice_ids) == 1:
                result['views'] = [(form_view_id, 'form')]
                result['res_id'] = invoice_ids.ids[0]
            else:
                result = {'type': 'ir.actions.act_window_close'}
            return result

class SaleAdvancePaymentInvExtension(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'
    

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        inv_obj = self.env['account.invoice']
        ir_property_obj = self.env['ir.property']

        account_id = False
        if self.product_id.id:
            account_id = self.product_id.property_account_income_id.id
        if not account_id:
            inc_acc = ir_property_obj.get('property_account_income_categ_id', 'product.category')
            account_id = order.fiscal_position_id.map_account(inc_acc).id if inc_acc else False
        if not account_id:
            raise UserError(
                _('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') %
                (self.product_id.name,))

        if self.amount <= 0.00:
            raise UserError(_('The value of the down payment amount must be positive.'))
        if self.advance_payment_method == 'percentage':
            amount = order.amount_untaxed * self.amount / 100
            name = _("Down payment of %s%%") % (self.amount,)
        else:
            amount = self.amount
            name = _('Down Payment')
        if order.fiscal_position_id and self.product_id.taxes_id:
            tax_ids = order.fiscal_position_id.map_tax(self.product_id.taxes_id).ids
        else:
            tax_ids = self.product_id.taxes_id.ids

        invoice = inv_obj.create({
            'name': order.client_order_ref or order.name,
            'origin': order.name,
            'type': 'out_invoice',
            'reference': False,
            'account_id': order.partner_id.property_account_receivable_id.id,
            'partner_id': order.partner_invoice_id.id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': name,
                'origin': order.name,
                'account_id': account_id,
                'price_unit': amount,
                'quantity': 1.0,
                'discount': 0.0,
                'uom_id': self.product_id.uom_id.id,
                'product_id': self.product_id.id,
                'sale_line_ids': [(6, 0, [so_line.id])],
                'invoice_line_tax_ids': [(6, 0, tax_ids)],
                'account_analytic_id': order.project_id.id or False,
            })],
            'currency_id': order.pricelist_id.currency_id.id,
            'payment_term_id': order.payment_term_id.id,
            'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
            'team_id': order.team_id.id,
            'comment': order.note,
            'inv_type':order.quote_type,
            'sale_project_id':self.sale_project_id and self.sale_project_id.id or False,
            'attention': order.attention,
        })
        
        inv_remarks_obj = self.env['invoice.remarks']
        if order.remarks_ids:
            for remarks in order.remarks_ids:
        	    invoice_remarks_vals = {
        	   	    'name': remarks.name and remarks.name.id or False,
        	   	    'invoice_id': invoice and invoice.id or False
        	    }
        	    inv_remarks_obj.create(invoice_remarks_vals)
        invoice.compute_taxes()
        invoice.message_post_with_view('mail.message_origin_link',
                    values={'self': invoice, 'origin': order},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return invoice
