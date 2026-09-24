# __manifest__.py
{
    'name': 'Product Multi Barcode Support',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Sales',
    'summary': 'Allows multiple products to share the same barcode with a selection popup in POS and Inventory.',
    'author': 'Bobur',
    'depends': ['product', 'point_of_sale', 'stock'],
    'data': [
        # 'security/ir.model.access.csv',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'product_barcode_support/static/src/app/popups/product_selection_popup.js',
            'product_barcode_support/static/src/app/popups/product_selection_popup.xml',
            'product_barcode_support/static/src/app/pos/pos_barcode_patch.js',
        ],
        'stock_barcode.assets_barcode': [
            'product_barcode_support/static/src/app/popups/product_selection_popup.js',
            'product_barcode_support/static/src/app/popups/product_selection_popup.xml',
            'product_barcode_support/static/src/app/inventory/inventory_barcode_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}