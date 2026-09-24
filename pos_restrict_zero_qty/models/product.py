from odoo import models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_product_stock_info(self, product_id):
        session = self.env['pos.session'].search([
            ('state', '=', 'opened'),
            ('user_id', '=', self.env.user.id)
        ], limit=1)
        config = session.config_id if session else self.env['pos.config'].search([], order='id desc', limit=1)

        if not config:
            return {"error": "Konfiguratsiya topilmadi."}
        picking_type = config.picking_type_id
        warehouse = picking_type.warehouse_id 
        
        product = self.browse(product_id)
        location_id = warehouse.lot_stock_id.id
        qty = product.with_context(location=location_id).qty_available
        
        return {
            "product_name": product.display_name,
            "warehouse_name": warehouse.name, 
            "picking_type_name": picking_type.name,
            "qty": qty
        }