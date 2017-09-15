# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api, _
from odoo.tools import amount_to_text_en

class InvoiceExtension(models.Model):
    _inherit = 'account.invoice'
    
    
    def convert(self, amount, cur):
        amount_in_words = amount_to_text_en.amount_to_text(amount, 'en', cur)
        words = amount_in_words.upper()
        return words
    
    @api.model
    def _default_payment_term(self):
        payment_term = self.env['account.payment.term'].search([('name','=','Cash/Cheque/Bank Transfer')])
        payment_term_id = payment_term and payment_term.id or False
        return payment_term_id
    
    inv_type = fields.Selection([
                                   ('led_strip','LED Strip Invoice'),
                                   ('led_attach','LED Attachments Invoice')
                                 ],string="Invoice Type",readonly=True)
    attention = fields.Char("Attention")
    prepared_by = fields.Many2one("res.users",'Prepared By')
    approved_by = fields.Many2one("res.users",'Approved By')
    sale_project_id = fields.Many2one('sale.project','Project')
    remarks_ids = fields.One2many('invoice.remarks','invoice_id','Remarks')
    payment_term_text = fields.Char('Payment Term')
    reference_no = fields.Char('Reference No')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term',
        readonly=True, states={'draft': [('readonly', False)]},
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. If you keep the payment term and the due date empty, it means direct payment. "
             "The payment term may compute several due dates, for example 50% now, 50% in one month.",default=_default_payment_term)
    
    
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        account_id = False
        payment_term_id = False
        fiscal_position = False
        bank_id = False
        company_id = self.company_id.id
        p = self.partner_id if not company_id else self.partner_id.with_context(force_company=company_id)
        type = self.type
        if p:
            rec_account = p.property_account_receivable_id
            pay_account = p.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

            if type in ('out_invoice', 'out_refund'):
                account_id = rec_account.id
                payment_term_id = p.property_payment_term_id.id
            else:
                account_id = pay_account.id
                payment_term_id = p.property_supplier_payment_term_id.id
            addr = self.partner_id.address_get(['delivery'])
            fiscal_position = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id, delivery_id=addr['delivery'])

            bank_id = p.bank_ids and p.bank_ids.ids[0] or False

            # If partner has no warning, check its company
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                    p = p.parent_id
                warning = {
                    'title': _("Warning for %s") % p.name,
                    'message': p.invoice_warn_msg
                    }
                if p.invoice_warn == 'block':
                    self.partner_id = False
                return {'warning': warning}

        self.account_id = account_id
        #self.payment_term_id = payment_term_id
        self.fiscal_position_id = fiscal_position

        if type in ('in_invoice', 'in_refund'):
            self.partner_bank_id = bank_id
    
    
    @api.model
    def get_line_length(self,line):
        limit = 7
        line_length = len(line)
        final_limit = limit - line_length
        if len(line) == 2:
            final_limit = final_limit - 1
        if len(line) == 3:
            final_limit = final_limit - 2
        if len(line) == 4:
            final_limit = final_limit - 3
        if len(line) == 5:
            final_limit = final_limit - 4
        if len(line) == 6:
            final_limit = final_limit - 5
        if len(line) == 7:
            final_limit = final_limit - 6
        if len(line) >= 8:
            final_limit = 19
        return final_limit
    
    @api.model
    def get_commission_line_length(self,line):
        limit = 7
        line_length = len(line)
        final_limit = limit - line_length - 2
        if len(line) == 2:
            final_limit = final_limit - 1
        if len(line) == 3:
            final_limit = final_limit - 2
        if len(line) == 4:
            final_limit = final_limit - 3
        if len(line) == 5:
            final_limit = final_limit - 4
        if len(line) == 6:
            final_limit = final_limit - 5
        if len(line) == 7:
            final_limit = final_limit - 6
        if len(line) >= 8:
            final_limit = 19
        return final_limit
    
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
        
    @api.multi
    def invoice_validate(self):
        inoive_tax = self.env['account.invoice.tax']
        new_tax_ids = []
        if self.amount_tax:
            print "\n\n\nself.amount_tax",self.amount_tax
            account = self.env['account.account'].search([('code','=','204002')]) #101300
            vals = {
                'account_id':account.id,
                'name':'Sales Tax',
                'amount':self.amount_tax,
                'invoice_id':self.id,
            }
            tax_id = inoive_tax.create(vals)
            new_tax_ids.append(tax_id.id)
        if self.amount_commission:
            account = self.env['account.account'].search([('code','=','502006')]) #100000
            vals = {
                'account_id':account.id,
                'name':'Referral Fees',
                'amount':self.amount_commission,
                'invoice_id':self.id,
            }
            tax_id = inoive_tax.create(vals)
            new_tax_ids.append(tax_id.id)
        self.write({'tax_line_ids': [(6,0,new_tax_ids)]})
        return super(InvoiceExtension, self).invoice_validate()

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

            if self.product_id.type == 'service':
                self.is_service = True
            else:
                self.is_service = False 
            
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
    is_service = fields.Boolean(string="Is Service")
    

class InvoiceRemarks(models.Model):
    _name = 'invoice.remarks'
    _description = 'Invoice Remarks'
    
    name = fields.Many2one('remarks.remarks','Remarks')
    invoice_id = fields.Many2one('account.invoice','Invoice')
    
