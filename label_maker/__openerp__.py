{
	'name': 'Product packaging manager',
	'version': '1.0',
	'category': 'Product',
	'summary': 'Enables customizable label making for product packaging',
	'description': 'Enables customizable label making for product packaging, box definition',
	'author': 'GigraphixDevOps',
	'depends': ['product', 'sale', 'report', 'website', 'base'],
	'data': [
		'views/product_view.xml',
		'views/label_maker_view.xml',
		'views/box_view.xml',
		'views/var_cat_view.xml'
	],
	'installable': True,
	'auto_install': False,
	'application': True,
}