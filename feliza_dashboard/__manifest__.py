# -*- coding: utf-8 -*-
{
    "name": "Feliza Dashboard",
    "version": "19.0.2.3.0",
    "category": "Sales/Point of Sale",
    "summary": "Savdo tarmog'i uchun boshqaruv paneli — rahbar va do'kon boshlig'i",
    "description": """
FELIZA DASHBOARD
================
Savdo tarmog'i uchun boshqaruv paneli. Ikki xil ko'rinish:

  * "Dashboard: Rahbar"         — barcha do'konlar, tannarx va marja bilan
  * "Dashboard: Do'kon boshlig'i" — faqat o'z do'koni, TANNARXSIZ

MUHIM: tannarx/marja ajratilishi SERVER tomonida amalga oshadi. Do'kon
boshlig'i guruhidagi foydalanuvchiga tannarx umuman hisoblanmaydi va
javobda bunday maydon bo'lmaydi — brauzerdan ham ko'rib bo'lmaydi.

AVTOMATIK MOSLASHUV: modul o'rnatilganda bazadagi maydonlarni o'zi
tekshiradi (sotuvchi maydoni, chegirma, o'lcham atributi va h.k.) va
mavjudlariga moslashadi. Qo'shimcha modul talab qilmaydi — faqat
standart "point_of_sale" va "stock" yetarli.

Aniqlangan moslashuvni "Dashboard > Sozlamalar > Diagnostika" bo'limida
ko'rish mumkin.

2.0: KAMOMAT bo'limi. "O'tkazma" yonida yangi oyna — do'konga kam yetib
borgan yuklar: qaysi jo'natma bo'yicha, qaysi do'konda, qaysi tovardan
qancha kam chiqqani, skladga qaytarilgan-qaytarilmagani. Manba —
warehouse_transfer_custom_19v 1.5+ maydonlari; modul eski bo'lsa bo'lim
umuman ko'rinmaydi.

2.2.0: ZAKUPCHI STATISTIKASI — uch yangi bo'lim (rahbar ham ko'radi,
zakupchi FAQAT o'z tovarlarini ko'radi):
  · Sotuvlarim — status (eng ko'p sotilgan / eng daromadli / minus
    foyda / savdosi past), qidiruv, kategoriya-rang-o'lcham filtrlari;
    sotuvda necha kun, kuniga o'rtacha, tan narx, sotuv narx, marja.
  · Skladim — kam qolgan / ko'p sonli / qolmagan, keltirgan marjasi.
  · Daromadim — komissiya jonli hisoblanadi (UZB 1.5%, import 1%),
    kunlik grafik, davlat va filial bo'yicha, tovar qidiruvi.

2.1.0: ZAKUPCHI PANELI. Yangi "Dashboard: Zakupchi" guruhi va "Zakup"
bo'limi: yo'ldagi yuklar (kutilayotgan kirimlar, kechikkanlari bilan),
yo'ldagi tovarlar, davrdagi zakuplar va ta'minotchilar, so'nggi kelgan
yuklar, tugab borayotgan tovarlar (sotuv sur'atiga nisbatan zaxira).
Zakupchi sotuv tushumini va marjani KO'RMAYDI — faqat dona va zakup
summalari. UI: kartalarga mayin soya, tab/jadval/fokus holatlari
sayqallandi — joylashuv o'zgarmadi.

2.0.1: bo'lim bor-yo'qligi endi Python maydoni emas, BAZADAGI USTUN
bo'yicha aniqlanadi. Shu tufayli modul fayllari yangilanib, baza
yangilanmagan holatda ham "column does not exist" xatosi chiqmaydi:
1.5 da aniq miqdor ustuni yo'q — o'shanda product_uom_qty ishlatiladi.
    """,
    "author": "Claude for Feliza",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "stock", "product"],
    "data": [
        "security/feliza_dashboard_groups.xml",
        "security/ir.model.access.csv",
        "views/feliza_target_views.xml",
        "views/pos_config_views.xml",
        "views/res_users_views.xml",
        "views/feliza_dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "feliza_dashboard/static/src/scss/dashboard.scss",
            "feliza_dashboard/static/src/js/dashboard.js",
            "feliza_dashboard/static/src/xml/dashboard.xml",
        ],
        # Odoo 19 qorong'i rejimda BOSHQA bundle yuboradi (body'ga class
        # qo'ymaydi) — web/views/webclient_templates.xml:300.
        # Faqat shu bundle'ga qo'shilgan fayl qorong'i rejimda ishlaydi.
        "web.assets_web_dark": [
            "feliza_dashboard/static/src/scss/dashboard.dark.scss",
        ],
    },
    "installable": True,
    "application": True,
}
