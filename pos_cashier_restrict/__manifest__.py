{
    'name': 'POS Cashier Restrict',
    'version': '19.0.1.0.1',
    'summary': 'Restrict POS discount and price buttons per cashier (employee)',
    'author': 'Custom',
    'category': 'Point of Sale',
    'depends': ['point_of_sale', 'hr', 'pos_hr'],
    'data': [
        'views/hr_employee_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cashier_restrict/static/src/js/pos_restrict.js',
            'pos_cashier_restrict/static/src/xml/pos_restrict.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
