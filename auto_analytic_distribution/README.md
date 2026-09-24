# Auto Analytic Distribution by Journal

## Maqsad
Bu modul kassadan chiqim/kirim kiritganda **Журнал** (Journal) asosida **Аналитическое распределение** (Analytic Distribution) ni avtomatik to'ldirib beradi.

## Muammo
- Naqd D3 jurnalida chiqim kiritilganda, analitik hisob qo'lda "Seul D3" tanlanishi kerak edi
- Har safar qo'lda tanlash noqulay va xatolarga olib keladi

## Yechim
- Har bir jurnal (Naqd D1, D2, D3, D4) uchun default analitik distribyutsiya sozlanadi
- Chiqim/kirim kiritganda avtomatik ravishda shu analitik hisob tanlanadi

---

## O'rnatish bo'yicha ko'rsatmalar

### 1. Modulni yuklab olish
Bu papkani Odoo addons papkasiga joylashtiring:
```
/path/to/odoo/addons/auto_analytic_distribution/
```

### 2. Odoo serverini qayta ishga tushirish
```bash
sudo systemctl restart odoo
# yoki
sudo service odoo restart
```

### 3. Apps ro'yxatini yangilash
1. Odoo'ga administrator sifatida kiring
2. **Apps** menyusiga o'ting
3. **Update Apps List** tugmasini bosing
4. "Auto Analytic Distribution by Journal" modulini qidiring
5. **Install** tugmasini bosing

---

## Sozlash bo'yicha ko'rsatmalar

### 1. Jurnallarga analitik hisob biriktirish

**Бухгалтерия → Конфигурация → Журналы**

Har bir jurnal uchun:

1. **Naqd D3** jurnalini oching
2. **Default Analytic Distribution** maydoniga:
   - **Seul D3** analitik hisobini tanlang
   - Foizni kiriting (odatda 100%)
3. **Saqlash**

Xuddi shu tartibda qolgan jurnallar uchun ham:
- **Naqd D1** → **Solnichniy D1**
- **Naqd D2** → **Solnichniy D2**  
- **Naqd D3** → **Seul D3**
- **Naqd D4** → Tegishli analitik hisob

### 2. Test qilish

1. **Бухгалтерия** menyusiga o'ting
2. **Cash In/Out** ochiladi
3. **Naqd D3** jurnalini tanlang
4. Chiqim summasini kiriting
5. **Аналитическое распределение** maydoni avtomatik ravishda **Seul D3** ga o'rnatilishini tekshiring

---

## Qo'shimcha imkoniyatlar

### Bir necha analitik hisob (Odoo'da "tags" kabi)
Agar bir operatsiyada bir necha analitik hisob kerak bo'lsa:

```
Seul D3: 70%
Solnichniy D1: 30%
```

Bunday sozlash mumkin.

---

## Texnik ma'lumotlar

### Fayllar tuzilishi:
```
auto_analytic_distribution/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── account_journal.py    # Jurnalga yangi field
│   └── account_move.py        # Avtomatik to'ldirish logikasi
└── views/
    └── account_journal_views.xml  # UI qo'shimcha
```

### Ishlash prinsipi:
1. `account.journal` modeliga `default_analytic_distribution` field qo'shiladi
2. Chiqim/kirim yaratilganda `@api.onchange` orqali jurnal tekshiriladi
3. Agar jurnalda default analitik hisob bo'lsa, u avtomatik qo'llaniladi

---

## Muammolar va yechimlar

### Analitik hisob tanlanmayapti
- Jurnalda **Default Analytic Distribution** to'g'ri sozlanganini tekshiring
- Modulni o'chirib qayta yoqing
- Cache tozalang: **Settings → Technical → Clear Cache**

### Qo'lda o'zgartirish mumkinmi?
Ha! Avtomatik to'ldiriladi, lekin kerak bo'lsa qo'lda ham o'zgartirish mumkin.

### Eski operatsiyalar o'zgaradimi?
Yo'q, faqat **yangi** yaratilgan operatsiyalarga qo'llaniladi.

---

## Qo'llab-quvvatlash

Savollar bo'lsa yoki yordam kerak bo'lsa:
- Telegram: @kalilbr
- Email: support@kalilbr.uz

---

## Litsenziya
MIT License - erkin foydalanishingiz mumkin.
