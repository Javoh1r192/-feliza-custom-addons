# Feliza – POS Gift Card qisman ishlatish (Odoo 19)

## Nima qiladi

Standart Odoo gift card (vaucher) skanerlanganda avtomatik `min(balans, order summasi)`
yechadi va "Gift Card" reward qatorini tahrirlab bo'lmaydi. Bu modul kassirga
shu qatorning summasini **kamaytirishga** ruxsat beradi:

* Kiritilgan summa vaucher **balansidan** oshsa — rad etiladi (popup).
* Kiritilgan summa **order summasidan** oshsa — rad etiladi.
* `0` kiritilsa — qo'lda cheklov olib tashlanadi, standart (to'liq) hisobga qaytadi.
* Orderga keyin mahsulot qo'shilsa/olib tashlansa, kiritilgan summa saqlanib qoladi
  (Odoo reward qatorlarini qayta yaratganda ham).
* Sahifa yangilansa ham saqlanadi (order `uiState` IndexedDB'da).

Server tomonda (`pos.order.confirm_coupon_programs`):

* `loyalty_card` qatori `FOR UPDATE` bilan qulflanadi — ikki filial bir vaqtda
  bitta vaucherni ishlatsa, ikkinchisi haqiqiy balansni ko'radi.
* Yechilayotgan ball = order reward qatorlaridagi `points_cost` yig'indisi bo'lishi shart.
* Balans yetarli bo'lmasa `UserError`.

## Kassir uchun qadamlar

1. Mahsulotlarni o'tkazing.
2. Vaucher barcode'ini skanerlang (yoki "Enter Code"). "Gift Card" qatori paydo bo'ladi.
3. Shu qatorni tanlang → numpad'da **Price** → summani kiriting (masalan `200000`).
4. Qator `-200 000` bo'ladi, qolgan summa naqd/karta bilan to'lanadi.
5. Order yopilgach vaucher balansi shu summaga kamayadi; qoldiq boshqa
   do'konda ishlatilishi mumkin.

Agar POS sozlamasida "Restrict Price Modifications to Managers" yoqilgan bo'lsa,
Price bosilganda popup chiqadi — u ham shu tekshiruvlardan o'tadi.

## O'rnatish

`custom-addons` addons_path'da bo'lishi kerak. Apps → Update Apps List →
"Feliza - POS Gift Card qisman ishlatish" → Install. Ochiq POS sessiyalarini
yopib qayta oching (assets yangilanishi uchun).

## Odoo ichki API'ga bog'liqlik (yangilashda tekshirish kerak)

* `pos_loyalty` JS: `PosOrder._getRewardLineValuesDiscount`, `_updateRewardLines`,
  `_getRealCouponPoints`, `_getDiscountableOnOrder`
* `point_of_sale` JS: `OrderSummary._setValue`, `OrderSummary.setLinePrice`
* `pos_loyalty` Python: `pos.order.confirm_coupon_programs`

## Test senariylari

1. 500 000 vaucher, 300 000 order → skaner → qator `-300 000` (standart).
   Price → `200000` → qator `-200 000`. Yana mahsulot qo'shing → hali `-200 000`.
2. Price → `600000` → "balans yetarli emas" popup, qator o'zgarmaydi.
3. Order 300 000, Price → `400000` → "order'dan katta" popup.
4. Orderni yoping → Loyalty → Gift Cards: balans 300 000, history'da 200 000 "used".
5. Boshqa POS'da xuddi shu vaucher → 300 000 ko'rinadi va ishlaydi.
6. Ikki brauzerda bir vaqtda 300 000 dan ishlatib, ikkalasini ketma-ket yoping →
   ikkinchisi server xatosi beradi (balans 0).
