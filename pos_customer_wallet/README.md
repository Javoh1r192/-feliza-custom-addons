# Mijoz hamyoni (Cashback Wallet) — POS moduli

Odoo 19.0 uchun custom modul. **Cashback ballarini TO'PLASH (earn)** — to'liq
Odoo'ning o'zining native **Loyalty (Sodiqlik) dasturi** orqali, avvalgidek
davom etadi — bunga bu modul umuman aralashmaydi. Bu modul faqat **cashback
ballarini SARFLASH (spend)** tomonini qulaylashtiradi: mijoz to'plagan
ballarini POS'da mahsulot qatori yoki "Rewards" tugmasi orqali emas, balki
"Naqd"/"Karta" kabi **alohida to'lov usuli** orqali, xohlagan qisman
summada, balansdan oshmasdan ishlatadi.

## 1. O'rnatish

1. `pos_customer_wallet` papkasini serveringizdagi custom addons papkasiga
   nusxalang.
2. Odoo'ni qayta ishga tushiring (`--update=pos_customer_wallet` yoki
   Apps > Update Apps List).
3. Apps ro'yxatidan **"Mijoz hamyoni (Cashback Wallet) - POS"** ni toping va
   o'rnating.

## 2. Sozlash — bosqichma-bosqich

### 2.1. Cashback uchun Loyalty dasturini tanlash

Bu modul **allaqachon mavjud** (yoki yangi yaratilgan) Odoo Loyalty
dasturidan foydalanadi — o'zi hech qanday yangi ball tizimi yaratmaydi.

1. Agar hali yo'q bo'lsa: **Point of Sale > Mahsulotlar > Discount & Loyalty**
   bo'limida `program_type = Loyalty Cards` turidagi dastur yarating
   (masalan, nomi "Cashback"). Bu yerda:
   - **Rules** (qoidalar) bo'limida — mijoz necha foiz/necha ball to'plashini
     belgilang (masalan, "har 1000 so'mga 10 ball" yoki "sof summaning 1%").
   - **Rewards** (mukofotlar) bo'limida — kamida bitta **Discount** turidagi
     mukofot bo'lishi kerak, **Discount Mode = "... per point"** qilib
     sozlangan (masalan, "1 ball = 1 so'm"). Aynan shu qiymatdan bu modul
     ballarni so'mga avtomatik aylantiradi — qattiq kod qilib yozilmagan,
     shuning uchun bu yerdagi nisbatni istalganda o'zgartirishingiz mumkin.
2. **Point of Sale > Konfiguratsiya > Sozlamalar** ga o'ting, **"Mijoz
   hamyoni (Cashback)"** bo'limida shu dasturni tanlang.

### 2.2. "Cashback" to'lov usulini yaratish

1. **Point of Sale > Konfiguratsiya > To'lov usullari** > Yangi.
2. Nomi: masalan `Cashback`.
3. **"Mijoz hamyoni (Cashback) to'lovi"** katagini belgilang (bu — shu
   modul qo'shgan yangi maydon; Journal/Outstanding Account qatori yonida
   chiqadi).
4. Journal sifatida bank turidagi alohida jurnal tanlang (yoki yarating).
5. **Outstanding Account** maydonini o'zingizning buxgalteriya
   rejangizdagi mijozlarga bo'lgan cashback majburiyat schyotiga
   yo'naltiring (masalan, sizning holatingizda 6930). Bu — POS sessiyasi
   yopilganda, Odoo'ning o'z avtomatik mexanizmi orqali, cashback
   ishlatilgan summani savdo daromadi qarshisiga to'g'ri schyotga
   yozadi — buni qo'lda qilish shart emas.
6. Shu to'lov usulini kerakli POS konfiguratsiyasiga (Payment Methods)
   qo'shing.

## 3. Ishlash mantig'i (qisqacha)

| # | Talab | Qanday hal qilingan |
|---|---|---|
| Ball to'plash | O'zgarmaydi — to'liq Odoo Loyalty/pos_loyalty mexanizmi orqali, avvalgidek |
| Qisman ishlatish | Kassir "Cashback" tugmasini bosadi, summani raqamli klaviatura bilan xohlagancha o'zgartiradi |
| To'lov usuli sifatida | Cashback `pos.payment` (to'lov qatori) sifatida ishlaydi, savat/mahsulotga umuman tegmaydi |
| Balans ko'rinishi | To'lov ekranida banner: joriy balans (Loyalty balansidan hisoblangan) va shu buyurtmada ishlatilgan summa |
| Overdraft nazorati | Frontend (`pos_payment.js`) darhol cheklaydi; server (`res_partner.py::_wallet_spend`) yakuniy tekshiruvni bajaradi |
| Chekda alohida qator | Odoo cheki barcha to'lov usullarini o'z-o'zidan alohida ko'rsatadi — cashback shu ro'yxatda chiqadi |
| Audit tarixi | Standart Odoo `loyalty.history` yozuvi — mijoz kartochkasidagi "Cashback karta" tugmasi orqali ko'rinadi |

## 4. Balansni qo'lda to'ldirish / tuzatish

Bu uchun alohida vosita yaratilmagan — **Odoo'ning o'z, tayyor vositasidan**
foydalaning: **Point of Sale > Mahsulotlar > Discount & Loyalty** > dastur >
"Loyalty Cards" smart tugmasi > kerakli mijozning kartasi > **"Update
Balance"** amali. Mijoz kartochkasida ham (Kontaktlar) endi **"Cashback
karta"** tugmasi bor — to'g'ridan-to'g'ri o'sha mijozning kartasiga olib
boradi.

## 5. Test rejasi

- [ ] Cashback to'lov usuli tanlanganda savat/mahsulotlar ro'yxatiga
      hech qanday qator qo'shilmasligini tekshiring.
- [ ] Mijoz balansidan kam summa kiritib, qisman to'lovni yakunlang.
- [ ] Mijoz balansidan ko'p summa kiritishga urinib ko'ring — tizim
      avtomatik balans darajasiga tushirib qo'yishi kerak.
- [ ] To'lov ekranida balans banneri ko'rinishini tekshiring, va u
      mijozning "Cashback karta"sidagi ball × nisbat bilan mos kelishini
      tekshiring.
- [ ] Chekda cashback to'lov turlari qatorida (naqd/karta bilan bir
      qatorda) chiqishini tekshiring.
- [ ] Savdodan keyin mijozning Loyalty kartasidagi ball balansi to'g'ri
      kamayganini va "History"da yangi yozuv paydo bo'lganini tekshiring.
- [ ] Sessiyani yoping va hosil bo'lgan buxgalteriya provodkasini
      ko'zdan kechiring (2.2-band).

## 6. Ma'lum cheklovlar

- Bir vaqtning o'zida faqat **bitta** Loyalty dasturi "cashback" sifatida
  belgilanadi (Sozlamalar > Mijoz hamyoni). Agar bir nechta mijozga
  tegishli Loyalty dastur bo'lsa, faqat shu tanlangan dastur balansi
  to'lov usuli orqali sarflanadi.
- Reward konfiguratsiyasida "... per point" turidagi mukofot topilmasa,
  modul 1 ball = 1 valyuta birligi deb hisoblaydi va log'ga ogohlantirish
  yozadi — bu holatda Sozlamalar > Discount & Loyalty'dagi dastur
  sozlamasini tekshiring.
- Qaytarish (refund/return) uchun ballarni avtomatik qaytarish
  qilinmaydi — buning uchun native "Update Balance" vositasidan qo'lda
  foydalaning.
