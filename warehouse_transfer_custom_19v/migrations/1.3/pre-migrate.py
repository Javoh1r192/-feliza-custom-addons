# -*- coding: utf-8 -*-
"""MAVJUD QOIDALARNI MODULGA BIRIKTIRISH (1.2 -> 1.3)

MUAMMO
------
Feliza bazasidagi ikkita yozuv qoidasi (ir.rule) QO'LDA yaratilgan —
ularning modul belgisi (external ID) yo'q:

    * «Personal Transfers Only dostup»  -> stock.picking
    * «Personal Warehouse Only dostup»  -> stock.picking.type

Agar biz shunchaki data faylida yangi qoidalar e'lon qilsak, bazada
IKKITADAN global qoida paydo bo'lardi. Odoo global qoidalarni VA (AND)
bilan birlashtiradi — ya'ni cheklov yumshamasdan, aksincha qattiqlashardi
va xodim yana ham kamroq hujjat ko'rardi.

YECHIM
------
Data fayli yuklanishidan OLDIN (shuning uchun `pre-migrate`) mavjud
qoidalarni topib, ularga modul belgisini beramiz. Shundan keyin Odoo
data faylini o'sha qatorlarning USTIGA yozadi — dublikat yaratilmaydi.

XAVFSIZLIK
----------
* Mos qoida topilmasa — hech narsa qilinmaydi, data fayli qoidani o'zi
  yaratadi (toza bazada shunday bo'ladi).
* Bir nechta nomzod topilsa — eng mosi biriktiriladi, qolganlariga
  TEGILMAYDI, faqat log'ga ogohlantirish yoziladi.
* Hech qanday holatda mavjud qoida o'chirilmaydi yoki o'chirib
  qo'yilmaydi.
"""
import logging

_logger = logging.getLogger(__name__)

MODULE = "warehouse_transfer_custom_19v"

# (external ID, model, kutilayotgan nom)
RULES = [
    ("rule_stock_picking_allowed_warehouse",
     "stock.picking", "Personal Transfers Only dostup"),
    ("rule_stock_picking_type_allowed_warehouse",
     "stock.picking.type", "Personal Warehouse Only dostup"),
]


def _adopt(cr, xmlid, model, expected_name):
    cr.execute("""
        SELECT res_id FROM ir_model_data
         WHERE module = %s AND name = %s AND model = 'ir.rule'
    """, (MODULE, xmlid))
    if cr.fetchone():
        _logger.info("%s: «%s» allaqachon biriktirilgan", MODULE, xmlid)
        return

    # egasiz (external ID'siz) global qoidalarni topamiz
    cr.execute("""
        SELECT r.id, r.name
          FROM ir_rule r
          JOIN ir_model m ON m.id = r.model_id
     LEFT JOIN ir_model_data d
            ON d.model = 'ir.rule' AND d.res_id = r.id
         WHERE m.model = %s
           AND d.id IS NULL
           AND r.domain_force LIKE %s
           AND NOT EXISTS (
                 SELECT 1 FROM rule_group_rel g WHERE g.rule_group_id = r.id)
      ORDER BY r.id
    """, (model, "%allowed_user_ids%"))
    rows = cr.fetchall()

    if not rows:
        _logger.info("%s: %s uchun qo'lda yaratilgan qoida topilmadi — "
                     "data fayli yangisini yaratadi", MODULE, model)
        return

    chosen = next(
        (rid for rid, name in rows if (name or "").strip() == expected_name),
        rows[0][0])

    cr.execute("""
        INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
        VALUES (%s, %s, 'ir.rule', %s, false)
    """, (MODULE, xmlid, chosen))

    _logger.info("%s: %s qoidasi #%s modulga biriktirildi — "
                 "data fayli uni yangilaydi", MODULE, model, chosen)

    if len(rows) > 1:
        _logger.warning(
            "%s: %s uchun egasiz global qoida bittadan ko'p topildi: %s. "
            "#%s biriktirildi, qolganlariga tegilmadi — qo'lda ko'rib chiqing.",
            MODULE, model, [r[0] for r in rows], chosen)


def migrate(cr, version):
    if not version:            # yangi o'rnatish — data fayli o'zi yaratadi
        return
    for xmlid, model, name in RULES:
        _adopt(cr, xmlid, model, name)
