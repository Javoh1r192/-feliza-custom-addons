# Feliza — Qabulda o'lchamga taqsimlash (Odoo 19)

Rang bo'yicha buyurtma qilingan tovarni qabul (Поступление) bosqichida
o'lchamlarga (razmerlarga) bo'lib taqsimlash uchun modul.

## Muammo

Xarid jarayonida tovar faqat **rang** bo'yicha buyurtma qilinadi
(masalan: `qora — 50`, `qizil — 50`). Tovar omborga kelganda esa uni
**o'lchamlar** bo'yicha taqsimlash kerak: `qora` 50 tadan `S=10, M=20,
L=15, XL=5`. Buni qo'lda qilish noqulay.

## Yechim

Qabul ekraniga **"O'lchamlarga taqsimlash"** tugmasi qo'shiladi. Tugma
oyna ochadi: har bir rang uchun o'lchamlar bo'yicha miqdor kiritasiz,
tizim jami miqdor talabga tengligini tekshiradi va qabul qatorlarini
avtomatik ravishda rang+o'lcham variantlariga bo'lib beradi.

## O'rnatish

1. `feliza_size_split` papkasini Odoo `addons` yo'liga joylang.
2. Odooda **Приложения (Apps)** → ro'yxatni yangilang (Обновить список
   приложений) → "Feliza — Qabulda o'lchamga taqsimlash" ni o'rnating.

## Bir martalik sozlash

1. **Atributlar → O'lcham** ni oching, **"O'lcham atributi"** bayrog'ini
   belgilang.
2. O'lcham qiymatlariga bitta **"—" (belgilanmagan)** qiymat qo'shing va
   uning **"Belgilanmagan o'lcham"** bayrog'ini belgilang.
3. O'lcham kerak bo'ladigan tovar shablonlariga **Rang + O'lcham** ikkala
   atributni ham qo'shing (o'lcham qiymatlari sifatida "—" va haqiqiy
   o'lchamlar: S, M, L, XL, ...).

## Ishlatish

1. Xaridda tovarni `rang / —` varianti bo'yicha buyurtma qiling.
2. Tovar kelganda qabulni oching → **"O'lchamlarga taqsimlash"** tugmasini
   bosing.
3. Har bir rang uchun o'lchamlar bo'yicha son kiriting → **"Taqsimlash"**.
4. Qabulni odatdagidek tasdiqlang (Проверить). Tovar skladga o'lchamlar
   bo'yicha kiradi.

## Texnik jihatlar

- `product.attribute.is_size` — atribut o'lcham o'lchovi ekanini bildiradi.
- `product.attribute.value.is_size_placeholder` — "belgilanmagan" qiymat.
- Taqsimlash qabulni **tasdiqlashdan oldin** amalga oshiriladi: manba
  harakat rezervi bekor qilinib, o'lchamli variantlarga bo'linadi va qayta
  rezerv qilinadi. PO (xarid) bilan bog'lanish saqlanadi.

## Versiya

- Odoo **19.0**
- Bog'liqliklar: `stock`, `purchase`
