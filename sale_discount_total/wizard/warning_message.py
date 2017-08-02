# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.tools.translate import _
from datetime import datetime,tzinfo,timedelta
import time


class warning_message(models.TransientModel):
    _name = 'warning.message'
    
    message = fields.Text('Message', readonly='True')
    
    @api.multi
    def go_ahead(self):
        return True
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
