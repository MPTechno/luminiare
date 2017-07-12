# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.tools.translate import _
from datetime import datetime,tzinfo,timedelta
import time


class crm_to_quote_wizard(models.TransientModel):
    
    _name = 'crm.to.quote.wizard'
    
    quote_type = fields.Selection([('led_strip', 'LED Strip Quotation'),('led_attach', 'LED Attachment Quotation')], 'Quote Type', required=True, default='led_strip')
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
