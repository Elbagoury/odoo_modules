{
	'name': 'GLS labeling service',
	'author': 'GigraphixDevOps',
	'description': 'Creates parcels and product package labels for GLS',
	'depends': ['account', 'stock_picking_package_preparation', 'stock_picking_package_preparation_line'],
	'active': 'true',
	'application': 'false',
	'data': ['view/gls_view.xml', 'view/gls_parcel.xml']
}
