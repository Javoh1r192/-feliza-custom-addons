# -*- coding: utf-8 -*-
"""SERIYALARNI BAZADAGI HOLATGA QARAB BIR MARTA TO'LDIRISH

Modul o'rnatilganda seriyalar bo'sh bo'lsa, mavjud tovarlar tahlil
qilinib avtomat to'ldiriladi. Har bir seriya uchun:
  * kategoriyalar nomi bo'yicha topiladi (bazada rus tilida);
  * oxirgi artikul — o'sha prefiksdagi ENG KATTA mavjud raqam.

Ya'ni yangi tovar hech qachon eski raqam ustiga tushmaydi.
Keyin sozlamalardan qo'lda o'zgartirish mumkin.
"""
import logging

_logger = logging.getLogger(__name__)

# (seriya nomi, prefiks, kategoriya nomlari)
#  Kategoriya nomlari bazadagidek — rus tilida. Topilmasa, o'sha nom
#  o'tkazib yuboriladi, seriya baribir yaratiladi.
SEED = [
    ("Kiyim (1xxxxx)", "1",
     ["Верхняя одежда", "Нижняя одежда", "Комплект"]),
    ("Paypoq / kolgotki (2xxxxx)", "2",
     ["Аксессуар / Носки", "Аксессуар / Колготки"]),
    ("Bijuteriya (3xxxxx)", "3",
     ["Аксессуар"]),
    ("Atir (4xxxxx)", "4",
     ["Аксессуар / Атир"]),
    ("Bosh kiyim, ro'mol, remen (5xxxxx)", "5",
     ["Бош кийим", "Аксессуар / Ремен"]),
    ("Sumka (6xxxxx)", "6",
     ["Аксессуар / Сумка"]),
    ("Oyoq kiyim (7xxxxx)", "7",
     ["Обув"]),
]


# ────────────────────────────────────────────────────────────────────
#  KATEGORIYA NOMI BO'YICHA AVTO BIRIKTIRISH
# ────────────────────────────────────────────────────────────────────
#  Feliza kategoriyalari yassi ro'yxat: «Верхняя одежда / Куртка»
#  degan nomdagi kategoriyaning OTASI yo'q — slash faqat nom ichida.
#  Shuning uchun «ota kategoriyaga qarab topish» ishlamaydi va har bir
#  kategoriyani alohida biriktirish kerak.
#
#  Quyidagi qoidalar bazadagi HAQIQIY holatdan olingan: har bir
#  kategoriyadagi tovarlarning artikul prefiksi tekshirildi
#  (masalan «Верхняя одежда / Куртка» dagi 28 ta tovarning hammasi
#  1xxxxx, «Бош кийим / Шапка» dagi 11 tasi 5xxxxx).
#
#  (nom boshlanishi, prefiks) — birinchi mos kelgani yutadi,
#  shuning uchun aniqroq qoidalar yuqorida turadi.
NAME_RULES = [
    ("аксессуар / сумка", "6"),
    ("аксессуар / атир", "4"),
    ("аксессуар / носки", "2"),
    ("аксессуар / колготки", "2"),
    ("аксессуар / ремен", "5"),
    ("аксессуар / румол", "5"),
    ("аксессуар", "3"),          # бижутерия va boshqalar
    ("верхняя одежда", "1"),
    ("нижняя одежда", "1"),
    ("комплект", "1"),
    ("dvoyka", "1"),
    ("двойка", "1"),
    ("бош кийим", "5"),
    ("обув", "7"),
]


def map_categories_to_series(env):
    """Hali biriktirilmagan kategoriyalarni nomiga qarab seriyaga qo'shadi.

    Faqat QO'SHADI — mavjud biriktirishlarga tegmaydi. Shuning uchun
    xodim jadvalda qo'lda o'zgartirsa, keyingi yangilashda buzilmaydi.
    """
    Series = env["feliza.artikul.series"].sudo()
    Categ = env["product.category"].sudo()

    series_by_prefix = {}
    for s in Series.search([]):
        digits = "".join(c for c in (s.last_code or "") if c.isdigit())
        if digits:
            series_by_prefix.setdefault(digits[0], s)
    if not series_by_prefix:
        return

    mapped = Series.search([]).categ_ids
    qoshildi = {}

    for categ in Categ.search([]):
        if categ in mapped:
            continue
        nom = (categ.complete_name or categ.name or "").strip().lower()
        for boshlanish, prefix in NAME_RULES:
            if nom.startswith(boshlanish):
                series = series_by_prefix.get(prefix)
                if series:
                    series.write({"categ_ids": [(4, categ.id)]})
                    qoshildi.setdefault(series.name, []).append(
                        categ.complete_name)
                break

    for nom, cats in qoshildi.items():
        _logger.info("Feliza: «%s» seriyasiga %d ta kategoriya qo'shildi: %s",
                     nom, len(cats), ", ".join(cats[:8]))
    if not qoshildi:
        _logger.info("Feliza: biriktirilmagan kategoriya topilmadi")


def sync_series_last_code(env):
    """Seriyadagi «oxirgi artikul»ni bazadagi haqiqiy eng kattasiga tenglaydi.

    Faqat KO'TARADI, hech qachon tushirmaydi. Bu bazani eski nusxadan
    tiklaganda foyda beradi: raqam orqaga ketib, keyin band raqamlarni
    birma-bir o'tkazib yurishga to'g'ri kelmaydi.
    """
    Series = env["feliza.artikul.series"].sudo()
    for s in Series.search([]):
        digits = "".join(c for c in (s.last_code or "") if c.isdigit())
        if not digits:
            continue
        env.cr.execute("""
            SELECT MAX(default_code) FROM product_template
             WHERE default_code ~ %s
        """, ("^" + digits[0] + "[0-9]{5}$",))
        row = env.cr.fetchone()
        haqiqiy = row and row[0]
        if haqiqiy and haqiqiy.isdigit() and int(haqiqiy) > int(digits):
            _logger.info("Feliza: «%s» — oxirgi artikul %s dan %s ga "
                         "ko'tarildi", s.name, digits, haqiqiy)
            s.write({"last_code": haqiqiy})


def seed_artikul_series(env):
    Series = env["feliza.artikul.series"].sudo()
    if Series.search_count([]):
        return                      # allaqachon sozlangan — tegilmaydi

    Categ = env["product.category"].sudo()
    by_name = {}
    for c in Categ.search([]):
        by_name[(c.complete_name or "").strip()] = c
        by_name.setdefault((c.name or "").strip(), c)

    for seq, (name, prefix, categ_names) in enumerate(SEED, start=1):
        # o'sha prefiksdagi eng katta mavjud artikul
        env.cr.execute("""
            SELECT MAX(default_code) FROM product_template
             WHERE default_code ~ %s
        """, ("^" + prefix + "[0-9]{5}$",))
        row = env.cr.fetchone()
        last = (row and row[0]) or (prefix + "00000")

        categs = Categ.browse()
        for cn in categ_names:
            c = by_name.get(cn)
            if c:
                categs |= c
            else:
                _logger.info("Feliza: «%s» kategoriyasi topilmadi", cn)

        Series.create({
            "name": name,
            "sequence": seq * 10,
            "last_code": last,
            "categ_ids": [(6, 0, categs.ids)],
        })
        _logger.info("Feliza: seriya «%s» — oxirgi %s, %d kategoriya",
                     name, last, len(categs))
