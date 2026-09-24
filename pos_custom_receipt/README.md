# pos_custom_receipt — Odoo 19 versiyasi

Odoo 18 uchun yozilgan modul Odoo 19 API'siga moslashtirildi va haqiqiy
Odoo 19 kassasida sinovdan o'tkazildi.

## Nima qiladi

1. **Foizli chegirma alohida qator yaratmaydi** — loyalty/promotion mukofoti
   foizda bo'lsa, chegirma to'g'ridan-to'g'ri tovar qatorlariga yoziladi.
2. **Bir xil tovar + bir xil chegirmali qatorlar birlashtiriladi** (qty qo'shiladi).
3. **Tovar qatorida chegirma summasi** qizil belgida ko'rsatiladi (masalan `-20 000`).
4. **Chekda**: chegirma mukofot qatori ko'rsatilmaydi, uning o'rniga yakuniy
   summadan oldin bitta **«Chegirma»** qatori chiqadi.

## 18 → 19 da nima o'zgardi

| 18 | 19 |
|---|---|
| `@point_of_sale/app/store/pos_store` | `@point_of_sale/app/services/pos_store` |
| `@point_of_sale/app/store/pos_hook` (`usePos`) | kerak emas — olib tashlandi |
| `@point_of_sale/app/generic_components/orderline/orderline` | `@point_of_sale/app/components/orderline/orderline` |
| `line.get_discount()` / `set_discount()` | `getDiscount()` / `setDiscount()` |
| `line.get_quantity()` / `set_quantity()` | `getQuantity()` / `setQuantity()` |
| `this.get_order()` | `this.getOrder()` |
| chekda `props.data.orderlines` (matn) | `props.order` (obyekt) |
| narx matndan regex bilan ajratilardi | `displayPriceNoDiscount − displayPrice` |
| xpath `//li[contains(@t-if,'line.discount')]` | `//li[@t-if='vals.discount']` |
| chegirma qatori nom bo'yicha topilardi | `reward_id.reward_type === "discount"` |

## O'rnatish

```bash
# 1. Papkani custom-addons ichiga qo'ying
#    /root/dockerodoo/odoo/custom-addons/pos_custom_receipt

# 2. Odoo'ni qayta ishga tushiring
docker restart odoo_app
```

So'ng Odoo'da: **Apps → Update Apps List → `pos_custom_receipt` → Install**.
Kassani qayta oching (brauzerda `Ctrl+Shift+R`).

Talab: `point_of_sale` va `pos_loyalty` o'rnatilgan bo'lishi kerak (ikkalasi ham bor).

## Sinov natijasi

Toza Odoo 19.0 kassasida uch holat tekshirildi — brauzer konsolida **0 xato**:

| Holat | Natija |
|---|---|
| 10% foizli chegirma | Alohida qator yo'q; qatorda `10% discount off on 200 000` + qizil `-20 000`; ikki marta bosilgan tovar bitta qatorga (qty 2) birlashdi; chekda «Chegirma 20 000», Jami 180 000 |
| 30 000 aniq summali chegirma | Kassada mukofot qatori ko'rinadi; chekda u yashiriladi, «Chegirma 30 000», Jami 170 000 |
| Chegirmasiz sotuv | Hech qanday o'zgarish yo'q, «Chegirma» qatori chiqmaydi |
