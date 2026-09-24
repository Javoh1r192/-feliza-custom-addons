import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CURRENCY_COUNTRY_MAP = {
    'CNY': 'Xitoy',
    'TRY': 'Turkiya',
    'USD': 'Amerika',
    'EUR': 'Yevropa',
    'GBP': 'Angliya',
    'KRW': 'Koreya',
    'UZS': "O'zbekiston",
}


class PurchaseVariantWizard(models.TransientModel):
    _name = 'purchase.variant.wizard'
    _description = "Purchase uchun tez mahsulot va variant tanlash"

    purchase_order_id = fields.Many2one('purchase.order', required=True, readonly=True, ondelete='cascade')
    step = fields.Selection([('product', 'Mahsulot'), ('variants', 'Variantlar')], default='product', required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Mavjud mahsulot (qidiring)', domain=[('purchase_ok', '=', True)])
    product_name = fields.Char('Mahsulot nomi')
    categ_id = fields.Many2one('product.category', 'Kategoriya')
    base_price = fields.Float('Narx (hamma variant uchun)', digits='Product Price')
    base_qty = fields.Float('Miqdor (hamma variant uchun)',
                            digits='Product Unit of Measure')
    # Bitta rasm — HAMMA variantga. Rasm mahsulot kartochkasiga (template)
    # yoziladi, variantlar esa o'zining alohida rasmi bo'lmasa o'shani
    # ko'rsatadi. Ya'ni bir marta yuklash yetarli.
    product_image = fields.Image('Rasm (hamma variantga)',
                                 max_width=1920, max_height=1920)
    attribute_line_ids = fields.One2many('purchase.variant.wizard.attr', 'wizard_id', string="Atributlar")
    variant_line_ids = fields.One2many('purchase.variant.wizard.line', 'wizard_id', string='Variantlar')

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl(self):
        if self.product_tmpl_id:
            self.base_price = self.product_tmpl_id.standard_price
            self.product_name = False
            self.categ_id = False
            self.attribute_line_ids = [(5,)]
            # mavjud mahsulotning rasmi ko'rinib tursin — xodim uni
            # almashtirmoqchimi yoki yo'qmi, o'zi hal qiladi
            self.product_image = self.product_tmpl_id.image_1920

    def action_next(self):
        self.ensure_one()
        if not self.product_tmpl_id:
            if not self.product_name:
                raise UserError(_('Mahsulot nomini kiriting.'))
            # Kategoriya majburiy: artikul aynan shu kategoriyaning
            # seriyasidan olinadi. Kategoriyasiz yaratilgan tovarga
            # to'g'ri artikul berib bo'lmaydi.
            if not self.categ_id:
                raise UserError(_(
                    'Kategoriyani tanlang.\n\n'
                    'Artikul mahsulot kategoriyasiga qarab beriladi '
                    '(kiyim 1xxxxx, sumka 6xxxxx, atir 4xxxxx va h.k.). '
                    'Kategoriyasiz to\'g\'ri artikul berib bo\'lmaydi.'))
            attr_lines = []
            for al in self.attribute_line_ids:
                if al.attribute_id and al.value_ids:
                    attr_lines.append((0, 0, {'attribute_id': al.attribute_id.id, 'value_ids': [(6, 0, al.value_ids.ids)]}))
            # sudo(): xaridchida «Товары / Создать» huquqi bo'lmasligi
            # mumkin — mahsulotni tizimning boshqa joyida yaratish unga
            # kerak emas, faqat shu oynadan. Huquqni butun tizim bo'ylab
            # ochib qo'ygandan ko'ra, shu yagona nuqtani ochgan
            # xavfsizroq. (2026-09-01: «Ошибка доступа» shu sabab edi.)
            tmpl = self.env['product.template'].sudo().create({
                'name': self.product_name,
                'categ_id': self.categ_id.id if self.categ_id else False,
                'type': 'consu',
                'is_storable': True,
                'available_in_pos': True,
                'purchase_ok': True,
                'sale_ok': True,
                'purchase_method': 'purchase',
                'standard_price': self.base_price,
                'attribute_line_ids': attr_lines,
            })
            self.product_tmpl_id = tmpl.id
        variants = self.product_tmpl_id.product_variant_ids
        if not variants:
            raise UserError(_('Bu mahsulotning varianti topilmadi.'))
        self.variant_line_ids = [(5,)] + [
            (0, 0, {'product_id': v.id, 'price': self.base_price,
                    'qty': self.base_qty or 0.0})
            for v in variants]
        self._apply_image()
        self.step = 'variants'
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        self.step = 'product'
        return self._reopen()

    def action_apply_base_price(self):
        self.ensure_one()
        for line in self.variant_line_ids:
            line.price = self.base_price
        return self._reopen()

    def action_apply_base_qty(self):
        """Miqdorni bir marta yozib, hamma variantga qo'yish.

        Kiyimda ko'pincha har bir o'lchamdan bir xil miqdorda olinadi —
        har bir qatorga alohida yozib chiqish ortiqcha ish.
        """
        self.ensure_one()
        for line in self.variant_line_ids:
            line.qty = self.base_qty
        return self._reopen()

    def action_apply_all(self):
        """Narx va miqdorni birdaniga hamma variantga."""
        self.ensure_one()
        for line in self.variant_line_ids:
            line.price = self.base_price
            line.qty = self.base_qty
        return self._reopen()

    def _apply_image(self):
        """Rasmni MAHSULOT KARTOCHKASIGA yozadi.

        Nega templatega? Chunki variantning o'z rasmi bo'lmasa, u
        template rasmini ko'rsatadi — demak bitta rasm hamma rang/o'lcham
        uchun yetadi. Aynan bir rangga alohida surat kerak bo'lsa, uni
        keyin xarid qatoridagi «Rasm» ustunidan qo'yish mumkin.

        sudo(): xaridchida mahsulotni tahrirlash huquqi bo'lmasligi
        mumkin, lekin rasm qo'yish uning ishining bir qismi.
        """
        self.ensure_one()
        tmpl = self.product_tmpl_id
        if not tmpl or not self.product_image:
            return
        if tmpl.image_1920 != self.product_image:
            tmpl.sudo().write({'image_1920': self.product_image})
            _logger.info("Rasm mahsulotga yozildi: %s", tmpl.display_name)

    def action_add_to_order(self):
        self.ensure_one()
        lines = self.variant_line_ids.filtered(lambda l: l.qty > 0)
        if not lines:
            raise UserError(_('Kamida bitta variantga miqdor kiriting.'))
        order = self.purchase_order_id
        currency_name = order.currency_id.name if order.currency_id else ''
        country_val = CURRENCY_COUNTRY_MAP.get(currency_name, '')

        # Bir marta templateni olamiz (barcha variantlar bir templatega tegishli)
        tmpl = self.product_tmpl_id
        # rasm 1-bosqichda emas, 2-bosqichda qo'yilgan bo'lishi ham mumkin
        self._apply_image()

        for line in lines:
            self.env['purchase.order.line'].create({
                'order_id': order.id,
                'product_id': line.product_id.id,
                'name': line.product_id.display_name,
                'product_qty': line.qty,
                'price_unit': line.price,
                'product_uom_id': line.product_id.uom_id.id,
                'date_planned': fields.Datetime.now(),
            })

        # Davlatni template ga yozamiz
        if country_val and tmpl:
            try:
                tmpl.sudo().write({'x_studio_ishlab_chiqarilgan_davlat': country_val})
                _logger.info("Davlat '%s' mahsulotga yozildi: %s", country_val, tmpl.name)
            except Exception as e:
                _logger.warning("Davlat yozishda xato: %s", e)

        return {'type': 'ir.actions.act_window_close'}

    def _reopen(self):
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'view_mode': 'form', 'target': 'new', 'context': self.env.context}


class PurchaseVariantWizardAttr(models.TransientModel):
    _name = 'purchase.variant.wizard.attr'
    _description = 'Wizard atribut satri'

    wizard_id = fields.Many2one('purchase.variant.wizard', required=True, ondelete='cascade')
    attribute_id = fields.Many2one('product.attribute', string='Atribut', required=True)
    value_ids = fields.Many2many('product.attribute.value', 'pv_wiz_attr_val_rel', 'attr_line_id', 'value_id', string='Qiymatlar', domain="[('attribute_id', '=', attribute_id)]")


class PurchaseVariantWizardLine(models.TransientModel):
    _name = 'purchase.variant.wizard.line'
    _description = 'Wizard variant satri'

    wizard_id = fields.Many2one('purchase.variant.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Variant', readonly=True)
    qty = fields.Float('Miqdor', default=0.0, digits='Product Unit of Measure')
    price = fields.Float('Narx', digits='Product Price')
