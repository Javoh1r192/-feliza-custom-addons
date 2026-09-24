from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # ------------------------------------------------------------------
    #  RASM — to'g'ridan-to'g'ri xarid qatoridan
    #
    #  Yangi tovar kelganda uni suratga olib, shu yerning o'zida qo'yish
    #  kerak. Rasm alohida saqlanmaydi — u MAHSULOTNING o'z rasmi bo'lib
    #  yoziladi, shuning uchun darhol hamma joyda ko'rinadi: katalogda,
    #  POS'da, mahsulot kartochkasida.
    #
    #  `product.product.image_1920` Odoo'ning o'zida compute+inverse:
    #    * bitta variantli mahsulotda rasm TEMPLATE ga yoziladi
    #    * ko'p variantli mahsulotda faqat O'SHA VARIANTGA
    #  Ya'ni har bir rang uchun alohida surat qo'yish mumkin, «Dvoyka
    #  (кора)» va «Dvoyka (синий)» turli rasm oladi.
    #
    #  sudo(): xaridchida mahsulotni tahrirlash huquqi bo'lmasligi mumkin,
    #  lekin rasm qo'yish uning ishining bir qismi. Faqat rasm yoziladi,
    #  boshqa hech narsa o'zgarmaydi.
    # ------------------------------------------------------------------
    product_image = fields.Image(
        string="Rasm",
        compute='_compute_product_image',
        inverse='_inverse_product_image',
        readonly=False,
        store=False,
        max_width=1920,
        max_height=1920,
        help="Mahsulot surati. Shu yerga qo'yilgan rasm mahsulotning o'ziga "
             "yoziladi va katalogda ham, POS'da ham ko'rinadi.",
    )

    @api.depends('product_id', 'product_id.image_1920')
    def _compute_product_image(self):
        for line in self:
            line.product_image = (
                line.product_id.sudo().image_1920 if line.product_id else False
            )

    def _inverse_product_image(self):
        for line in self:
            if line.product_id:
                line.product_id.sudo().image_1920 = line.product_image
