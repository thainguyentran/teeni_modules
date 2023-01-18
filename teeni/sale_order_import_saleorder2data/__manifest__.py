{
    'name': 'Sale Order Import Invoice2data',
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'summary': 'Import customer sale order using the invoice2data lib',
    'author': 'Appex',
    'website': 'https://appex.co',
    'depends': ['sale_order_import'],
    'external_dependencies': {'python': ['invoice2data']},
    'data': ['wizard/sale_order_import_view.xml'],
    'demo': ['demo/demo_data.xml'],
    'installable': True,
}
