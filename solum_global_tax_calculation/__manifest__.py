{
    'name': 'Global Tax Calculation',
    'version': '1.0',
    'category': 'Tax Management',
    'summary': "Global Tax Calculation",
    'author': 'HashMicro/ Amit Patel',
    'website': 'www.hashmicro.com',
    'description': """
Global Tax Calculation in Sale and Invoice
=======================
1/ Restrict the odoo default tax calculation for each and every product line in Sale and Invoice

2/ Apply the tax globally in sale and invoice [Fixed Tax and based on the percentage]
	""",
    'depends': [
		'sale',
		'account',
		'sale_discount_total'
    ],
    'data': [
        'views/sale_view.xml',
        'views/account_invoice_view.xml',
    ],
    'demo': [],
    'images': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}
