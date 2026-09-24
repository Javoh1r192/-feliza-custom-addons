# Feliza POS Layout

Point of Sale (kassa) ekranida chap panelni **sudrab o'lchash** mumkin qiladi,
tanlangan kenglikni eslab qoladi va mahsulotlar setkasini ixchamlashtiradi.

## Imkoniyatlar

- **Sudrab o'lchash** — chap panelning o'ng chekkasidagi dastakni sichqoncha yoki
  **barmoq (sensor ekran)** bilan tortib kenglikni jonli o'zgartirasiz.
- **Eslab qolish** — tanlangan kenglik shu qurilmada saqlanadi (localStorage),
  POS qayta ochilганда tiklanadi.
- **Ikki marta bosish** — dastakni double-click qilsangiz standart kenglikка qaytadi.
- **Jonli px ko'rsatkichi** — tortayotganda joriy kenglik ko'rinib turadi.
- **Ixcham mahsulotlar** — o'ng tarafda bir ekranда ko'proq mahsulot sig'adi.
- **Mobil xavfsiz** — telefon ko'rinishida (< 993px) o'chirilgan.

## Boshlang'ich qiymatlarni o'zgartirish

`static/src/scss/pos_layout.scss` faylining boshidagi `:root` blokida:

- `--feliza-leftpane-default` — boshlang'ich kassa kengligi (Odoo standarti 450px)
- `--feliza-product-min-width` — mahsulot katakchasi kengligi (Odoo standarti 115px;
  kichikroq = ko'proq mahsulot)

Chegaralar (min/max kenglik) va sezgirlik `static/src/js/pos_resize.js` boshida:
`MIN_WIDTH`, `MAX_WIDTH`, `HANDLE_ZONE`.

O'zgartirgandan keyin modulni **Upgrade** qiling va POS'ni qayta oching
(brauzer keshini yangilang).

## Ishlatish

Kassa ekranida chap va o'ng panellar orasidagi chegaraga sichqonchani olib
boring — kursor `↔` ko'rinishга o'zgaradi. Bosib ushlab, chapga/o'ngga torting.
Sensor ekranda shu chegaradan barmoq bilan torting. Standartга qaytarish uchun
chegarани ikki marta bosing.

## O'rnatish

1. `feliza_pos_layout` papkasini Odoo `addons` (yoki `extra-addons`) katalogiга qo'ying.
2. Developer rejimida **Apps → Update Apps List**.
3. "Feliza POS Layout" ni qidiring va **Install** (agar oldingi versiya o'rnatilgan
   bo'lsa — **Upgrade**).
4. POS'ni qayta oching (ochiq bo'lsa brauzerни yangilang / keshни tozalang).

## Xavfsizlik / moslik

Faqat CSS va kichik mustaqil JS qo'shiladi — hech qanday Odoo modeli, OWL
komponenti yoki Python kodi o'zgartirilmaydi. `pos_product_exchange`,
`feliza_size_split` va boshqa modullar bilan to'liq mos keladi.
