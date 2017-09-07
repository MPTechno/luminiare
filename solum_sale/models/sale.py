# -*- coding: utf-8 -*-
import time
import datetime


from odoo import api, fields, models, exceptions, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError

class SaleExtenstion(models.Model):
    _inherit = 'sale.order'
    
    
    @api.model
    def get_line_length(self,line):
        limit = 7
        line_length = len(line)
        final_limit = limit - line_length
        if len(line) <= 1:
            final_limit = 1
        if len(line) == 2:
            final_limit = 0
        return final_limit
    
    def get_formated_date(self,date_order):
        if date_order:
            date = str(date_order).split(' ')
            date1 = datetime.datetime.strptime(date[0], '%Y-%m-%d')
            date2 = date1.strftime('%m/%d/%Y')
            return date2
        else:
        	return ''
    
    @api.multi
    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)]) if order.procurement_group_id else []
            order.delivery_count = len(order.picking_ids)

    
    @api.onchange('fiscal_position_id')
    def _compute_tax_id(self):
        """
        Trigger the recompute of the taxes if the fiscal position is changed on the SO.
        """
        for order in self:
            order.currency_id = self.env['res.currency'].search([('name', '=', 'SGD')])
            order.order_line._compute_tax_id()
    
    @api.onchange('payment_term_id')
    def _payment_term_id(self):
        for order in self:
            order.payment_term_text = self.payment_term_id.name
    
    
    def _calculateStateDays(self):
        diff_time = 0
        if self.state_change_date and self.state in ('draft','sent'):
            current_date_str = fields.Date.context_today(self)
            current_date = fields.Date.from_string(current_date_str)
            state_change_str = self.state_change_date
            state_change = fields.Date.from_string(state_change_str)
            diff_time = (current_date - state_change).days
            if diff_time >= 7:
                self.write({'state':'idle'})
        self.days_sice_state_change = diff_time
    
    
    @api.model
    def _default_payment_term(self):
        payment_term_id = self.env['account.payment.term'].search([('name','=','Cash/Cheque/Bank Transfer')])
        payment_term_id = payment_term_id and payment_term_id.id or False
        return payment_term_id
    
    quote_type = fields.Selection([('led_strip','LED Strip Quotation'),('led_attach','LED Attachments Quotaion')],
                                   string="Quotaion Type",readonly=True)
    state_when_idle = fields.Char(string="State when set Idle",readonly=True)
    attention = fields.Char("Attention")
    name_led_strip = fields.Many2one('res.users', string='Name', track_visibility='onchange', default=lambda self: self.env.user)
    email_led_strip = fields.Char("Email", default=lambda self: self.env.user.email)
    state_change_date = fields.Date(string="State Change Date")
    sale_project_id = fields.Many2one('sale.project','Project')
    days_sice_state_change = fields.Integer(compute=_calculateStateDays,string="Days Since Last State")
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Picking associated to this sale')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')
    remarks_ids = fields.One2many('sale.remarks','order_id','Remarks')
    client_order_ref_id = fields.Many2one('res.partner','Customer Reference')
    experation_terms_ids = fields.Many2one('experation.terms','Experation Terms')
    payment_term_text = fields.Char('Payment Term')
    reference_no = fields.Char('Reference No')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',oldname='payment_term',default=_default_payment_term)
    
    
    @api.model
    def default_get(self, fields):
        rec = super(SaleExtenstion, self).default_get(fields)
        remarks_ids_list = []
        if rec.has_key('quote_type') and rec['quote_type']:
		    if rec['quote_type'] == 'led_strip':
				for remarks_obj in self.env['remarks.remarks'].search(['|',('type','=','led_strip'),('type','=','Both')]):
				    remarks_line_vals = {
				        'name': remarks_obj and remarks_obj.id or False,
				        }
				    line_obj = self.env['sale.remarks'].create(remarks_line_vals)
				    remarks_ids_list.append(line_obj.id)
		    if rec['quote_type'] == 'led_attach':
				for remarks_obj in self.env['remarks.remarks'].search(['|',('type','=','led_attach'),('type','=','Both')]):
				    remarks_line_vals = {
				        'name': remarks_obj and remarks_obj.id or False,
				        }
				    line_obj = self.env['sale.remarks'].create(remarks_line_vals)
				    remarks_ids_list.append(line_obj.id)
        rec['remarks_ids'] = [(6, 0, remarks_ids_list)]
        return rec
    
    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment term
        - Invoice address
        - Delivery address
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                #'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            #'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        if self.env.user.company_id.sale_note:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note

        if self.partner_id.user_id:
            values['user_id'] = self.partner_id.user_id.id
        if self.partner_id.team_id:
            values['team_id'] = self.partner_id.team_id.id
        self.update(values)
    
    
    @api.multi
    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action
    
    @api.onchange('experation_terms_ids')
    def _experation_terms_ids(self):
        for order in self:
            date = str(order.date_order).split(' ')
            date_order = datetime.datetime.strptime(date[0], '%Y-%m-%d')
            order.validity_date = date_order + datetime.timedelta(days=int(self.experation_terms_ids.name))
    
    @api.multi
    def write(self,vals):
        if vals.get('state',False):
            vals.update({'state_change_date':fields.Date.context_today(self)})
        return super(SaleExtenstion,self).write(vals)
        
class SaleOrderLineExtension(models.Model):
    _inherit = 'sale.order.line'
    
    @api.model
    def _default_colour(self):
        colour_id = self.env['colour.colour'].search([('name','=','White')])
        colour_id = colour_id and colour_id.id or False
        return colour_id
    
    @api.multi
    @api.depends('sequence', 'order_id')
    def get_number(self):
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line:
                line.number = number
                number += 1
    
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id','length')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id)
            price_subtotal = 0.0
            #if line.length and line.length > 0.0:
            #    price_subtotal = (line.length/1000) * line.product_uom_qty * line.price_unit
            if line.product_id.uom_id.name == 'mm' or line.product_id.uom_id.name == 'MM':
                price_subtotal = (line.product_uom_qty/1000) * line.price_unit
            else:
                price_subtotal = taxes['total_excluded']
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': price_subtotal,
                'price_subtotal': price_subtotal,
                'net_price': price_subtotal,
            })
    
    
    net_price = fields.Monetary(compute='_compute_amount', string='Nett Price', readonly=True, store=True)
    image = fields.Binary(string="Image")
    area_id = fields.Many2one('area.area','Area')
    product_location_id = fields.Many2one('product.location','Location')
    length = fields.Float('Length(MM)')
    number = fields.Integer(compute='get_number', store=True ,string="Item")
    colour_id = fields.Many2one('colour.colour','Colour', default=_default_colour)
                                 
    
    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = 1.0

        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        name = ''
        if product.description_sale:
            name += product.description_sale
        vals['name'] = name

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price(self._get_display_price(product), product.taxes_id, self.tax_id)
        self.update(vals)

        title = False
        message = False
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s") % product.name
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            if product.sale_line_warn == 'block':
                self.product_id = False
            return {'warning': warning}
        return {'domain': domain}
    
    @api.multi
    @api.onchange('product_id')
    def onChnageProduct(self):
        if not self.product_id:
            self.update({
                'image': False,
            })
            return
        self.update({'image':self.product_id.image})
        
class ResCurrency(models.Model):
    _inherit = 'res.currency'
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        res = super(ResCurrency, self).name_search(name, args, operator, limit)
        result = []
        currency_ids = self.search(['|',('name','=','SGD'),('name','=','USD')])
        if currency_ids:
            for currency in currency_ids:
                result.append((currency.id,currency.name))
            return result
        else:
            return res
    
class ProductLocation(models.Model):
    _name = 'product.location'
    _description = 'Product Location'
    
    name = fields.Char(string='Location',required=True)

class ExperationTerms(models.Model):
    _name = 'experation.terms'
    _description = 'Experation Terms'
    
    name = fields.Integer(string='Experation Term',required=True)

class AreaArea(models.Model):
    _name = 'area.area'
    _description = 'Area'
    
    name = fields.Char(string='Name',required=True)

class SaleRemarks(models.Model):
    _name = 'sale.remarks'
    _description = 'Sale Remarks'
    
    name = fields.Many2one('remarks.remarks','Remarks')
    order_id = fields.Many2one('sale.order','Sale Order')
    
class RemarksRemarks(models.Model):
    _name = 'remarks.remarks'
    _description = 'Remarks'
    
    name = fields.Char(string='Name',required=True)
    type = fields.Selection([('led_strip','Strip Remark'),('led_attach','Attachment Remark'),('Both','Both')],string="Remark Type",readonly="True")
    
class Colour(models.Model):
    _name = 'colour.colour'
    _description = 'Color'
    
    name = fields.Char(string='Name',required=True)
    
class SaleProject(models.Model):
    _name = 'sale.project'
    _description = 'Project'
    
    name = fields.Char(string='Name',required=True)
