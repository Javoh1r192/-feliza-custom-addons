# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models
from odoo.fields import Domain


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'product.catalog.mixin']

    # ------------------------------------------------------------------
    # Product catalog integration
    # ------------------------------------------------------------------
    def _default_order_line_values(self, child_field=False):
        default_data = super()._default_order_line_values(child_field)
        new_default_data = self.env['stock.move']._get_product_catalog_lines_data()
        return {**default_data, **new_default_data}

    def _get_product_catalog_domain(self):
        # Только физические товары (склад. учёт): исключаем услуги и наборы.
        # type == 'consu' покрывает и складируемые, и расходуемые товары.
        domain = super()._get_product_catalog_domain() & Domain('type', '=', 'consu')
        # Для отгрузок и внутренних перемещений показываем только товары,
        # у которых есть остаток (qty_available > 0). Для приёмок (incoming)
        # фильтр не нужен — туда приходуют новый товар с нулевым остатком.
        if self.picking_type_code in ('outgoing', 'internal'):
            domain &= Domain('qty_available', '>', 0)
        return domain

    def _get_action_add_from_catalog_extra_context(self):
        # Остаток («On Hand») и фильтр qty_available считаются по исходному
        # складу/локации документа — так в каталоге видно наличие именно там,
        # откуда уходит/перемещается товар.
        ctx = super()._get_action_add_from_catalog_extra_context()
        if self.picking_type_code in ('outgoing', 'internal') and self.location_id:
            ctx['location'] = self.location_id.id
        return ctx

    # ------------------------------------------------------------------
    # Остаток на карточке каталога
    # ------------------------------------------------------------------
    #  Раньше остаток использовался ТОЛЬКО как фильтр
    #  (_get_product_catalog_domain -> qty_available > 0), но на самой
    #  карточке не показывался. Теперь он передаётся во фронтенд полем
    #  `qtyAvailable` и выводится рядом с ценой и артикулом.
    # ------------------------------------------------------------------

    def _catalog_qty_location(self):
        """Локация, по которой считается остаток в первом числе карточки.

        Для отгрузок и внутренних перемещений — исходная локация документа
        (откуда уходит товар). Для приёмок — склад документа целиком.
        """
        self.ensure_one()
        if self.picking_type_code in ('outgoing', 'internal') and self.location_id:
            return self.location_id
        wh = self.picking_type_id.warehouse_id
        return wh.view_location_id if wh else self.env['stock.location'].browse()

    def _catalog_qty_context(self):
        """Контекст для штатных вычислений Odoo (домен каталога)."""
        self.ensure_one()
        ctx = {}
        if self.picking_type_code in ('outgoing', 'internal') and self.location_id:
            ctx['location'] = self.location_id.id
        elif self.picking_type_id.warehouse_id:
            ctx['warehouse_id'] = self.picking_type_id.warehouse_id.id
        return ctx

    def _catalog_qty_sql(self, location, product_ids):
        """{product_id: остаток} по поддереву локации — прямым запросом.

        ПОЧЕМУ SQL, А НЕ product.qty_available:

        1) Модуль warehouse_transfer_custom_19v ставит на stock.quant
           ГЛОБАЛЬНОЕ правило «Personal Stock (Astatka) Only»: сотрудник
           магазина видит кванты только своего склада. Через ORM остаток
           чужого склада вернулся бы НУЛЁМ — а вся эта подсказка нужна
           именно для того, чтобы видеть чужой (основной) склад.

        2) `qty_available` объявлен без `uid` в depends_context, поэтому
           его значение в кэше ОБЩЕЕ для sudo и обычного пользователя.
           Если раньше в том же запросе поле посчитал обычный пользователь,
           последующий sudo-вызов вернул бы его (нулевое) значение из кэша.
           Проверено на живой базе. Запрос к БД от кэша не зависит.

        Показывается только количество: работать с чужим складом это не
        позволяет и себестоимость не раскрывает.
        """
        self.ensure_one()
        if not location or not product_ids:
            return {}
        self.env.cr.execute("""
            SELECT q.product_id, COALESCE(SUM(q.quantity), 0)
              FROM stock_quant q
              JOIN stock_location l ON l.id = q.location_id
             WHERE l.usage = 'internal'
               AND l.parent_path LIKE %s
               AND q.product_id = ANY(%s)
               AND q.company_id = ANY(%s)
             GROUP BY q.product_id
        """, (location.parent_path + '%', list(product_ids),
              self.env.companies.ids))
        return {r[0]: float(r[1] or 0) for r in self.env.cr.fetchall()}

    def _catalog_main_warehouses(self):
        """Склады, остаток которых показывается на карточке справочно.

        ПРИОРИТЕТ — «Склад-получатель» документа (destination_warehouse_id):
        заявка идёт именно туда, поэтому в каталоге показываем наличие в
        ВЫБРАННОМ складе-получателе. Так магазин сразу видит, сколько товара
        уже есть там, куда он оформляет доставку.

        Если поле «Склад-получатель» не заполнено (или модуль перемещений
        не установлен) — старое поведение: склады с флагом feliza_catalog_main.

        Склад самого документа исключается: его остаток уже показан первым
        числом, повторять незачем.
        """
        self.ensure_one()
        Wh = self.env['stock.warehouse'].sudo()
        own = self.picking_type_id.warehouse_id

        # 1) «Склад-получатель» (Qabul qiluvchi ombor) — главный приоритет.
        dest = self.destination_warehouse_id \
            if 'destination_warehouse_id' in self._fields else Wh.browse()
        if dest and (not own or dest.id != own.id):
            return dest.sudo()

        # 2) Fallback — склады с флагом feliza_catalog_main.
        if 'feliza_catalog_main' not in Wh._fields:
            return Wh.browse()
        mains = Wh.search([
            ('company_id', 'in', self.env.companies.ids),
            ('feliza_catalog_main', '=', True),
        ], order='sequence, id')
        if own:
            mains = mains.filtered(lambda w: w.id != own.id)
        return mains[:3]

    def _get_product_catalog_order_data(self, products, **kwargs):
        res = super()._get_product_catalog_order_data(products, **kwargs)
        ids = products.ids
        mains = self._catalog_main_warehouses()
        # По одному запросу на локацию, а не на карточку.
        qty_map = self._catalog_qty_sql(self._catalog_qty_location(), ids)
        main_maps = {
            wh.id: self._catalog_qty_sql(wh.view_location_id, ids)
            for wh in mains
        }
        for product in products:
            res[product.id] |= self._get_product_price_and_data(
                product, qty=qty_map.get(product.id, 0.0),
                mains=mains, main_maps=main_maps)
        return res

    def _get_product_price_and_data(self, product, qty=None,
                                    mains=None, main_maps=None):
        """Данные о товаре для карточки каталога.

        price / uomDisplayName — штатные,
        qtyAvailable          — остаток в исходной локации документа,
        mainStocks            — [{name, qty}] по справочным складам.
        """
        self.ensure_one()
        if qty is None:
            qty = self._catalog_qty_sql(
                self._catalog_qty_location(), product.ids).get(product.id, 0.0)
        data = {
            'price': product.standard_price,
            'uomDisplayName': product.uom_id.display_name,
            'qtyAvailable': qty,
        }
        if mains is None:
            mains = self._catalog_main_warehouses()
        if mains:
            main_maps = main_maps or {}
            rows = []
            for wh in mains:
                m = main_maps.get(wh.id)
                if m is None:
                    m = self._catalog_qty_sql(wh.view_location_id, product.ids)
                rows.append({'name': wh.name, 'qty': m.get(product.id, 0.0)})
            data['mainStocks'] = rows
        return data

    def _get_product_catalog_record_lines(self, product_ids, **kwargs):
        """Строки перемещения документа, сгруппированные по товару."""
        grouped_lines = defaultdict(lambda: self.env['stock.move'])
        for move in self.move_ids:
            if move.product_id.id not in product_ids:
                continue
            grouped_lines[move.product_id] |= move
        return grouped_lines

    def _is_readonly(self):
        """Документ доступен только для чтения, если завершён или отменён."""
        self.ensure_one()
        return self.state in ('done', 'cancel')

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """Создать/обновить/удалить строку перемещения для товара из каталога."""
        self.ensure_one()
        moves = self.move_ids.filtered(lambda m: m.product_id.id == product_id)
        if moves:
            if quantity != 0:
                moves[0].product_uom_qty = quantity
            elif self.state == 'draft':
                moves.unlink()
                return 0
            else:
                moves[0].product_uom_qty = 0
        elif quantity > 0:
            self.env['stock.move'].create(
                self._prepare_catalog_move_vals(product_id, quantity)
            )
        product = self.env['product.product'].browse(product_id)
        return self._get_product_price_and_data(product)['price']

    def _prepare_catalog_move_vals(self, product_id, quantity):
        """Значения для создания stock.move из каталога."""
        self.ensure_one()
        Move = self.env['stock.move']
        product = self.env['product.product'].browse(product_id)
        vals = {
            'picking_id': self.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id': product.id,
            'product_uom_qty': quantity,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
        }
        # Совместимость по версиям/конфигурациям: задаём поля, только если они есть.
        if 'name' in Move._fields:
            vals['name'] = product.display_name
        if 'product_uom' in Move._fields:
            vals['product_uom'] = product.uom_id.id
        return vals
