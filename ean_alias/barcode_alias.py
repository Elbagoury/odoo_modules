from openerp import fields, models, api, _

class BarcodeAlias(models.Model):
    _name = "barcode.alias"

    name = fields.Char(string="Note")
    ean = fields.Char(string="EAN Code")
    product_id = fields.Integer(string="Product ID")

class ProductProduct(models.Model):
    _inherit = "product.product"

    barcode_aliases = fields.One2many('barcode.alias', 'product_id', string="Barcode Aliases")

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def process_barcode_from_ui(self, cr, uid, picking_id, barcode_str, visible_op_ids, context=None):
        '''This function is called each time there barcode scanner reads an input'''
        lot_obj = self.pool.get('stock.production.lot')
        package_obj = self.pool.get('stock.quant.package')
        product_obj = self.pool.get('product.product')
        stock_operation_obj = self.pool.get('stock.pack.operation')
        stock_location_obj = self.pool.get('stock.location')
        answer = {'filter_loc': False, 'operation_id': False}
        #check if the barcode correspond to a location
        matching_location_ids = stock_location_obj.search(cr, uid, [('loc_barcode', '=', barcode_str)], context=context)
        if matching_location_ids:
            #if we have a location, return immediatly with the location name
            location = stock_location_obj.browse(cr, uid, matching_location_ids[0], context=None)
            answer['filter_loc'] = stock_location_obj._name_get(cr, uid, location, context=None)
            answer['filter_loc_id'] = matching_location_ids[0]
            return answer
        #check if the barcode correspond to a product
        matching_product_ids = product_obj.search(cr, uid, ['|', ('ean13', '=', barcode_str), ('default_code', '=', barcode_str)], context=context)

        if not matching_product_ids:
            alias_ids = self.pool.get('barcode.alias').search(cr, uid, [('ean', '=', barcode_str)], context=context)
            if alias_ids:
                aliases = self.pool.get('barcode.alias').browse(cr, uid, alias_ids, context=None)

                matching_product_ids = [x.product_id for x in aliases]
        print "MATCHING PRODUCT IDS 1"
        print matching_product_ids
        if matching_product_ids:
            op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id, [('product_id', '=', matching_product_ids[0])], filter_visible=True, visible_op_ids=visible_op_ids, increment=True, context=context)
            answer['operation_id'] = op_id
            return answer
        #check if the barcode correspond to a lot
        matching_lot_ids = lot_obj.search(cr, uid, [('name', '=', barcode_str)], context=context)
        if matching_lot_ids:
            lot = lot_obj.browse(cr, uid, matching_lot_ids[0], context=context)
            op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id, [('product_id', '=', lot.product_id.id), ('lot_id', '=', lot.id)], filter_visible=True, visible_op_ids=visible_op_ids, increment=True, context=context)
            answer['operation_id'] = op_id
            return answer
        #check if the barcode correspond to a package
        matching_package_ids = package_obj.search(cr, uid, [('name', '=', barcode_str)], context=context)
        if matching_package_ids:
            op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id, [('package_id', '=', matching_package_ids[0])], filter_visible=True, visible_op_ids=visible_op_ids, increment=True, context=context)
            answer['operation_id'] = op_id
            return answer
        return answer
