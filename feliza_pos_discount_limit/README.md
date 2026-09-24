# Feliza POS Discount Limit

Har bir foydalanuvchi / kassir uchun POS kassada bera oladigan **maksimal chegirma
foizini** cheklaydi.

## Nima qiladi

- Foydalanuvchi (Sozlamalar → Foydalanuvchilar) va xodim (Xodimlar) kartochkasiga
  **"POS chegirma"** sahifasi qo'shiladi, unda **"POS: Maksimal chegirma (%)"** maydoni.
- Standart qiymat **100%** = cheksiz. Cheklamoqchi bo'lgan kassirga masalan **25**
  qo'yasiz — u kassada 25% dan ortiq chegirma bera olmaydi.
- Kassada limitdan oshiq chegirma kiritilsa, avtomatik limitgacha kamayadi va
  ogohlantirish chiqadi (numpad `%`, barcode — barcha yo'llar qamrab olingan).
- **Server tomonida ham** tekshiriladi — frontendni chetlab o'tib ham limitdan
  oshiq chegirmali buyurtma saqlanmaydi.

## Qayerga qo'yiladi (foydalanuvchi vs xodim)

- Kassirlar **o'z Odoo useri** bilan kirsa → **Foydalanuvchi** kartochkasidagi
  maydonni to'ldiring.
- Kassirlar **PIN/beyji (xodim)** bilan kirsa → **Xodim** kartochkasidagi maydonni
  to'ldiring.
- Ikkovi ham qo'llab-quvvatlanadi; ikkalasi to'ldirilgan bo'lsa, kassadagi amaldagi
  kassir (xodim) ustunlik qiladi.

Managerlar/adminlarni cheklamaslik uchun ularning maydonini **100** da qoldiring.

## O'rnatish

1. `feliza_pos_discount_limit` papkasini serverdagi `custom-addons` ga qo'ying.
2. `chmod -R 755` bilan ruxsat bering, Odoo konteynerini restart qiling.
3. Odoo → developer rejimi → **Apps → Update Apps List** → "Feliza POS Discount
   Limit" ni **Install**.
4. Kerakli kassirlarga limit foizini yozing, POS'ni `Ctrl+F5` bilan yangilang.

## Xavfsizlik / moslik

Hech qanday Odoo modeli yoki template REPLACE qilinmaydi — faqat maydon qo'shiladi,
view'ga sahifa qo'shiladi va POS store metodi patch qilinadi. Boshqa POS modullari
(`pos_product_exchange`, `pos_cashier_restrict`, `sensible_pos_access_rights_employee`
va h.k.) bilan mos ishlaydi.
