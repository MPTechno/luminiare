{
    'name': 'Global Discount on Sale and Invoice',
    'version': '1.0',
    'category': 'Sales Management',
    'summary': "Global Discount on Sale and Invoice",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'http://www.cybrosys.com',
    'description': """
Sale Discount for Total Amount
=======================
Global Discount on Sale and Invoice.
""",
    'depends': [
    	'sale',
        'account',
        'solum_sale',
        'solum_invoice'
    ],
    'data': [
        'views/sale_view.xml',
        'views/account_invoice_view.xml',
        'views/res_config_view.xml',
        'wizard/warning_message_view.xml',
        'data/ir_config_parameter_data.xml',
    ],
    'demo': [],
    'images': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}
