from odoo import models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_product_stock_info(self, product_id, config_id=False):
        if config_id:
            config = self.env['pos.config'].browse(config_id)
        else:
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

    @api.model
    def get_products_stock_info(self, product_ids, config_id=False):
        """Bir nechta mahsulot qoldig'ini bitta so'rovda qaytaradi.

        Eski `get_product_stock_info` o'zgarishsiz qoldirildi — u har bir
        tovarga alohida chaqirilardi. Bu metod savatdagi hamma tovarni
        bitta so'rovda tekshiradi.

        Qaytadi: {"<product_id>": {"product_name", "warehouse_name", "qty"}}
        yoki konfiguratsiya topilmasa {"error": ...}
        """
        if config_id:
            config = self.env['pos.config'].browse(config_id)
        else:
            session = self.env['pos.session'].search([
                ('state', '=', 'opened'),
                ('user_id', '=', self.env.user.id)
            ], limit=1)
            config = session.config_id if session else self.env['pos.config'].search([], order='id desc', limit=1)

        if not config:
            return {"error": "Konfiguratsiya topilmadi."}

        picking_type = config.picking_type_id
        warehouse = picking_type.warehouse_id
        location_id = warehouse.lot_stock_id.id
        products = self.browse(product_ids).exists().with_context(location=location_id)
        return {
            str(product.id): {
                "product_name": product.display_name,
                "warehouse_name": warehouse.name,
                "picking_type_name": picking_type.name,
                "qty": product.qty_available,
            }
            for product in products
        }
