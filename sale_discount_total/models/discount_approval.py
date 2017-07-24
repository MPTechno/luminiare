from odoo import api, fields, models



class AccountDiscountSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    discount_limit = fields.Float(string="Discount limit in %",help="Discount limit for the Quotation comfirmation and Invoice Validation")
    
    @api.model
    def get_default_discount_limit(self, fields):
        discount_limit = self.env.ref('sale_discount_total.discount_limit_verification').value
        return {'discount_limit': float(discount_limit)}

    @api.multi
    def set_default_discount_limit(self):
        for record in self:
            self.env.ref('sale_discount_total.discount_limit_verification').write({'value': float(record.discount_limit)})


