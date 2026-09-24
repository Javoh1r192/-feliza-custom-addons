# Feliza POS Stock Visibility

## Muammo

`stock.quant` ga qo'yilgan record rule (foydalanuvchi faqat o'z ombori qoldig'ini
ko'radi) POS mahsulot ma'lumot oynasidagi **"Sklad"** ro'yxatiga ham ta'sir qiladi.
Natijada kassirga boshqa omborlar **0** bo'lib ko'rinadi.

## Yechim

Bu modul POS ko'rsatish metodini (`get_product_info_pos`) **sudo** bilan qayta
hisoblaydi — faqat KO'RSATISH uchun. Shunda:

- **POS'da** — barcha ombor qoldig'i to'liq ko'rinadi (record rule to'smaydi).
- **Backend (Inventory / astatka)** — record rule o'z kuchida qoladi, foydalanuvchi
  faqat o'z ombori qoldig'ini ko'radi.

Record rule O'ZGARTIRILMAYDI — uni o'chirmang, o'zi kerak. Bu modul faqat POS
ko'rsatishini to'g'rilaydi.

## O'rnatish

1. Papkani `custom-addons` ga qo'ying, `chmod -R a+rX`, `docker restart odoo_app`.
2. Apps → "Feliza POS Stock Visibility" → Install.
3. POS'ni `Ctrl+F5` bilan yangilang, mahsulot ma'lumot oynasini oching — barcha
   ombor qoldig'i ko'rinishi kerak.

## Eslatma

Agar POS'da kassirga **faqat o'z ombori** qoldig'i ko'rinsin (boshqa omborlar umuman
ko'rinmasin) desangiz — bu modul kerak emas, faqat record rule yetadi. Bu modul aksincha,
POS'da HAMMA ombor ko'rinishi uchun.
