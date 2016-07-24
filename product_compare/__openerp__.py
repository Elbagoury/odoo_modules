{
	'name': 'Product compare',
	'author': 'GigraphixDevOps',
	'description': 'Compares products in master ODOO with products in slave ODOOs',
	'depends': ['product'],
	'data': ['view/product_compare_view.xml', 'view/product_category_compare.xml'],
	'application': True,
	'installable': True,
	'active': True
}