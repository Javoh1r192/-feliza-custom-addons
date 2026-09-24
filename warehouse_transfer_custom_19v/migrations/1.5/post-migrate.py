# -*- coding: utf-8 -*-
"""1.5 — KAMOMAT

1) Endi keraksiz bo'lgan ikkita hisobot menyusi o'chiriladi
   (yozuv o'chirilmaydi, faqat yashiriladi — kerak bo'lsa qaytarish
   uchun bitta `active = true` yetadi).

2) «Kamomat» menyusi va u ochadigan oynaning nomi uchta tilda
   yoziladi: ingliz — Shortfall, rus — Недостача, o'zbek — Kamomat.
"""
import logging

_logger = logging.getLogger(__name__)

# xmlid -> o'chiriladigan menyular
OCHIRILADI = [
    ("ombor_hisoboti_19v", "menu_warehouse_monthly_report"),
    ("warehouse_transfer_custom_19v", "menu_stock_move_interwh_report"),
]

NOMLAR = {
    "en_US": "Shortfall",
    "ru_RU": "Недостача",
    "uz_UZ": "Kamomat",
}


def _res_id(cr, modul, nom, model):
    cr.execute(
        "SELECT res_id FROM ir_model_data "
        " WHERE module = %s AND name = %s AND model = %s",
        (modul, nom, model))
    row = cr.fetchone()
    return row[0] if row else None


def migrate(cr, version):
    if not version:
        return

    # --- 1. keraksiz menyular -----------------------------------------
    for modul, nom in OCHIRILADI:
        rid = _res_id(cr, modul, nom, "ir.ui.menu")
        if not rid:
            continue
        cr.execute("UPDATE ir_ui_menu SET active = false WHERE id = %s", (rid,))
        _logger.info("Feliza kamomat: %s.%s menyusi yashirildi", modul, nom)

    # --- 2. Kamomat menyusi/oynasi nomi tillarga bo'yicha --------------
    # Faol tillar bo'yicha faqat mavjudlari yoziladi.
    cr.execute("SELECT code FROM res_lang WHERE active")
    faol = {r[0] for r in cr.fetchall()} or {"en_US"}
    nom_json = {k: v for k, v in NOMLAR.items() if k in faol}
    if "en_US" not in nom_json:
        nom_json["en_US"] = NOMLAR["en_US"]

    import json
    js = json.dumps(nom_json)

    rid = _res_id(cr, "warehouse_transfer_custom_19v", "menu_kamomat",
                  "ir.ui.menu")
    if rid:
        cr.execute("UPDATE ir_ui_menu SET name = %s WHERE id = %s", (js, rid))

    rid = _res_id(cr, "warehouse_transfer_custom_19v", "action_kamomat",
                  "ir.actions.act_window")
    if rid:
        cr.execute("UPDATE ir_act_window SET name = %s WHERE id = %s",
                   (js, rid))

    _logger.info("Feliza kamomat: menyu nomlari yozildi (%s)",
                 ", ".join(sorted(nom_json)))
