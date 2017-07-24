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
    

class InvoiceLineExtension(models.Model):
    _inherit = 'account.invoice.line'
    
    
    
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
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        net_price = 0.0
        if self.quantity > 0:
        	if taxes:
        	    net_price = taxes['total_included'] / self.quantity
    	self.net_price = net_price
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
    
    net_price = fields.Monetary(string='Nett Price',store=True, readonly=True, compute='_compute_price')
    product_location_id = fields.Many2one('product.location','Location')
    number = fields.Integer(compute='get_number', store=True ,string="Item")
    length = fields.Char('Length(MM)')
    

class InvoiceRemarks(models.Model):
    _name = 'invoice.remarks'
    _description = 'Remarks'
    
    name = fields.Char(string='Remarks',required=True)
    invoice_id = fields.Many2one('account.invoice','Invoice')
