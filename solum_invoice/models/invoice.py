# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api

class InvoiceExtension(models.Model):
    _inherit = 'account.invoice'
    
    inv_type = fields.Selection([
                                   ('led_strip','LED Strip Invoice'),
                                   ('led_attach','LED Attachments Invoice')
                                 ],string="Invoice Type",readonly=True)
    attention = fields.Char("Attention")
    prepared_by = fields.Many2one("res.users",'Prepared By')
    approved_by = fields.Many2one("res.users",'Approved By')
    crm_lead_id = fields.Many2one('crm.lead','Project')
    remarks_ids = fields.One2many('invoice.remarks','invoice_id','Remarks')
    payment_term_text = fields.Char('Payment Term')
    reference_no = fields.Char('Reference No')
    
    @api.onchange('payment_term_id')
    def _payment_term_id(self):
        for invoice in self:
            invoice.payment_term_text = self.payment_term_id.name
    
    @api.model
    def default_get(self, fields):
        rec = super(InvoiceExtension, self).default_get(fields)
        remarks_ids_list = []
        if rec.has_key('inv_type') and rec['inv_type']:
		    if rec['inv_type'] == 'led_strip':
				for remarks_obj in self.env['remarks.remarks'].search(['|',('type','=','led_strip'),('type','=','Both')]):
				    remarks_line_vals = {
				        'name': remarks_obj and remarks_obj.id or False,
				        }
				    line_obj = self.env['invoice.remarks'].create(remarks_line_vals)
				    remarks_ids_list.append(line_obj.id)
		    if rec['inv_type'] == 'led_attach':
				for remarks_obj in self.env['remarks.remarks'].search(['|',('type','=','led_attach'),('type','=','Both')]):
				    remarks_line_vals = {
				        'name': remarks_obj and remarks_obj.id or False,
				        }
				    line_obj = self.env['invoice.remarks'].create(remarks_line_vals)
				    remarks_ids_list.append(line_obj.id)
        rec['remarks_ids'] = [(6, 0, remarks_ids_list)]
        return rec


class InvoiceLineExtension(models.Model):
    _inherit = 'account.invoice.line'
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        if not self.invoice_id:
            return

        part = self.invoice_id.partner_id
        fpos = self.invoice_id.fiscal_position_id
        company = self.invoice_id.company_id
        currency = self.invoice_id.currency_id
        type = self.invoice_id.type

        if not part:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a partner!'),
                }
            return {'warning': warning}

        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            if part.lang:
                product = self.product_id.with_context(lang=part.lang)
            else:
                product = self.product_id

            self.name = ''
            account = self.get_invoice_line_account(type, product, fpos, company)
            if account:
                self.account_id = account.id
            self._set_taxes()

            if type in ('in_invoice', 'in_refund'):
                if product.description_purchase:
                    self.name += product.description_purchase
            else:
                if product.description_sale:
                    self.name += product.description_sale

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

            if company and currency:
                if company.currency_id != currency:
                    self.price_unit = self.price_unit * currency.with_context(dict(self._context or {}, date=self.invoice_id.date_invoice)).rate

                if self.uom_id and self.uom_id.id != product.uom_id.id:
                    self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
        return {'domain': domain}
    
    @api.model
    def _default_colour(self):
        colour_id = self.env['colour.colour'].search([('name','=','White')])
        colour_id = colour_id and colour_id.id or False
        return colour_id
    
    @api.multi
    @api.depends('sequence', 'invoice_id')
    def get_number(self):
        for invoice in self.mapped('invoice_id'):
            number = 1
            for line in invoice.invoice_line_ids:
                line.number = number
                number += 1
    
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id','length')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        price_subtotal = 0.0
        price_subtotal_signed = 0.0
        #if self.length and self.length > 0.0:
        #    price_subtotal = price_subtotal_signed = (self.length/1000) * self.quantity * self.price_unit
        if self.product_id.uom_id.name == 'mm' or self.product_id.uom_id.name == 'MM':
            price_subtotal = price_subtotal_signed = (self.quantity/1000) * self.price_unit
        else:
            price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price    
        self.price_subtotal = price_subtotal
        net_price = 0.0
        #if self.quantity > 0:
        #	if taxes:
        #	    net_price = taxes['total_included'] / self.quantity
    	self.net_price = self.price_subtotal
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
    
    net_price = fields.Monetary(string='Nett Price',store=True, readonly=True, compute='_compute_price')
    area_id = fields.Many2one('area.area','Area')
    product_location_id = fields.Many2one('product.location','Location')
    number = fields.Integer(compute='get_number', store=True ,string="Item")
    length = fields.Float('Length(MM)')
    colour_id = fields.Many2one('colour.colour','Colour', default=_default_colour)
    

class InvoiceRemarks(models.Model):
    _name = 'invoice.remarks'
    _description = 'Invoice Remarks'
    
    name = fields.Many2one('remarks.remarks','Remarks')
    invoice_id = fields.Many2one('account.invoice','Invoice')
