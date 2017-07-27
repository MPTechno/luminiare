{
    'name': 'Global Commission Calculation',
    'version': '1.0',
    'category': 'Commission Management',
    'summary': "Global Commission Calculation",
    'author': 'HashMicro/ Amit Patel',
    'website': 'www.hashmicro.com',
    'description': """ Global Commission Calculation in Sale and Invoice """,
    'depends': [
		'sale',
		'account',
		'sale_discount_total',
		'solum_global_tax_calculation',
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
