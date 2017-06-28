# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api

class InvoiceExtension(models.Model):
    _inherit = 'account.invoice'
    
    inv_type = fields.Selection([
                                   ('led_strip','LED Strip Invoice'),
                                   ('led_attach','LED Attachments Invoice')
                                 ],string="Invoice Type",readonly=True)
    
