/** @odoo-module **/
/*
 * FELIZA POS CHEKI
 *
 * Odoo'ning standart cheki buyurtmachi talabiga to'g'ri kelmadi:
 * QR kod, soliq qatorlari va MXIK kodlari joy egallaydi, kerakli
 * ma'lumot (sotuvchi, mijoz, bonuslar) esa umuman yo'q.
 *
 * Shu sababli chek shabloni BUTUNLAY almashtiriladi. Hisob-kitobning
 * o'zi Odoo'niki bo'lib qoladi — biz faqat ko'rsatamiz. Ayniqsa
 * bonuslar: `order.getLoyaltyPoints()` — Odoo'ning o'z metodi,
 * shuning uchun chekdagi raqam bilan bazadagi qoldiq HAR DOIM mos
 * keladi. O'zimiz qayta hisoblaganimizda ular ajralib ketardi.
 */
import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

/** So'm: tiyinsiz, mingliklar probel bilan — 235 000 */
function pul(qiymat) {
    const butun = Math.round(qiymat || 0);
    return butun.toLocaleString("ru-RU").replace(/ | |,/g, " ");
}

/** Dona: butun bo'lsa kasrsiz */
function son(qiymat) {
    const q = qiymat || 0;
    return Math.abs(q - Math.round(q)) < 0.001
        ? String(Math.round(q))
        : q.toFixed(2);
}

// Chek shabloni to'liq bizniki
patch(OrderReceipt, { template: "feliza_pos_chek.FelizaReceipt" });

patch(OrderReceipt.prototype, {
    // ---------------- sarlavha ----------------
    get felizaCfg() {
        return this.order.config || {};
    },
    get felizaLogo() {
        // Modul ichidagi TOZA QORA logotip. POS sozlamasiga yuklangan
        // rasm bej (och jigarrang) edi — termal printer uni deyarli
        // ko'rinmas kulrang dog' qilib chiqarardi. Termal chek uchun
        // rang faqat 100% qora bo'lishi kerak, shuning uchun logotipni
        // qora-oq qilib modulning o'ziga joyladik: har bir kassada
        // hech narsa sozlamasdan bir xil, tiniq chiqadi.
        return "/feliza_pos_chek/static/img/chek_logo.png";
    },

    // ---------------- odamlar ----------------
    get felizaKassir() {
        return this.order.getCashierName() || "—";
    },
    get felizaSotuvchi() {
        // `pos_salesperson` moduli qo'shgan maydon. POS'da hali
        // tanlanmasa bo'sh keladi — o'ylab topmaymiz, chiziqcha qo'yamiz.
        const s = this.order.salesperson_emp_id;
        if (s && typeof s === "object" && s.name) {
            return s.name;
        }
        return "—";
    },
    get felizaMijoz() {
        return this.order.partner_id?.name || "—";
    },

    // ---------------- chek raqami va sana ----------------
    get felizaChekRaqam() {
        const ref = this.order.pos_reference || "";
        const bolak = ref.split("-");
        return bolak.length > 1 ? bolak[bolak.length - 1]
                                : (this.order.tracking_number || ref || "—");
    },
    get felizaSana() {
        const d = this.order.date_order;
        try {
            return d?.toFormat ? d.toFormat("dd.MM.yyyy HH:mm") : "";
        } catch {
            return "";
        }
    },

    // ---------------- tovarlar ----------------
    get felizaQatorlar() {
        return (this.order.lines || [])
            .filter((l) => !l.combo_parent_id)
            .map((line) => {
                const jami = line.priceInclNoDiscount ?? line.priceIncl ?? 0;
                const miqdor = line.qty || 0;
                const birlik = miqdor ? jami / miqdor : jami;
                const artikul = line.product_id?.default_code || "";
                const chap = (artikul ? artikul + " · " : "")
                    + son(miqdor) + " x " + pul(birlik);
                return {
                    nom: line.full_product_name || line.product_id?.display_name || "",
                    chap: chap,
                    summa: pul(jami),
                };
            });
    },

    // ---------------- yakuniy summalar ----------------
    get felizaChegirmaSoni() {
        return this.order.getTotalDiscount ? this.order.getTotalDiscount() : 0;
    },
    get felizaTolandiSoni() {
        return this.order.priceIncl || 0;
    },
    get felizaJami() {
        return pul(this.felizaTolandiSoni + this.felizaChegirmaSoni);
    },
    get felizaChegirma() {
        return pul(this.felizaChegirmaSoni);
    },
    get felizaTolandi() {
        return pul(this.felizaTolandiSoni);
    },
    get felizaTolovlar() {
        return this.paymentLines.map((p) => ({
            nom: p.payment_method_id?.name || "",
            summa: pul(p.getAmount()),
        }));
    },

    // ---------------- hamyon (pos_customer_wallet) ----------------
    /**
     * "Cashback" TO'LOV USULI orqali to'langan summa (so'mda).
     *
     * pos_customer_wallet moduli cashback'ni REWARD sifatida emas,
     * TO'LOV USULI sifatida sarflaydi — shuning uchun bu sarf
     * `getLoyaltyPoints()` ning `spent` qiymatiga KIRMAYDI va uni
     * alohida qo'shib hisoblash shart. Modul o'rnatilmagan bo'lsa
     * `is_wallet_payment` maydoni umuman bo'lmaydi va bu 0 qaytaradi.
     */
    get felizaHamyonSum() {
        try {
            return (this.paymentLines || [])
                .filter((pl) => pl.payment_method_id
                             && pl.payment_method_id.is_wallet_payment)
                .reduce((jami, pl) => jami + (pl.getAmount() || 0), 0);
        } catch {
            return 0;
        }
    },

    /** 1 ball nechchi so'm — hamyon dasturining per_point mukofotidan
     *  (pos_customer_wallet dagi hisob bilan bir xil; odatda 1). */
    get felizaHamyonKurs() {
        try {
            const models = this.order.models;
            const cfg = models["pos.config"]
                && models["pos.config"].getFirst
                && models["pos.config"].getFirst();
            const dastur = cfg && cfg.company_id
                && cfg.company_id.pos_wallet_loyalty_program_id;
            if (!dastur) {
                return 1;
            }
            const mukofot = models["loyalty.reward"].find(
                (r) => r.program_id && r.program_id.id === dastur.id
                    && r.reward_type === "discount"
                    && r.discount_mode === "per_point");
            return mukofot && mukofot.discount ? mukofot.discount : 1;
        } catch {
            return 1;
        }
    },

    // ---------------- bonuslar ----------------
    get felizaBonus() {
        if (typeof this.order.getLoyaltyPoints !== "function") {
            return null;      // pos_loyalty o'rnatilmagan
        }
        let stat;
        try {
            stat = this.order.getLoyaltyPoints();
        } catch {
            return null;
        }
        if (!stat || !stat.length) {
            return null;
        }

        let qoshildi = 0;
        let olindi = 0;
        let boredi = 0;
        for (const s of stat) {
            const p = s.points || {};
            const won = p.won || 0;
            const spent = p.spent || 0;
            qoshildi += won;
            olindi += spent;

            // `balance` — mijoz kartasidagi ochkolar. Uning MA'NOSI
            // uch holatda uch xil, buni sinovda aniqladik:
            //
            //  1) karta bor + chek yopilgan  -> balance SAVDODAN KEYINGI
            //     qoldiq (POS uni sinxronda yangilaydi);
            //  2) karta bor + chek ochiq     -> balance savdodan OLDINGI;
            //  3) karta yo'q (yangi mijoz)   -> balance 0 bo'lib qoladi,
            //     chunki POS uni faqat xotirada yaratadi va yangilamaydi.
            //
            // Shuning uchun har uchalasini alohida hisoblaymiz — aks
            // holda bitta savdo ikki marta qo'shilib ketardi.
            const yangiKarta = !s.couponId || Number(s.couponId) === 0;
            if (yangiKarta) {
                boredi += 0;
            } else if (this.order.finalized) {
                boredi += (p.balance || 0) - won + spent;
            } else {
                boredi += p.balance || 0;
            }
        }
        // Cashback TO'LOV USULI bilan to'langan qism ham kartadan
        // yechiladi (server: pos_customer_wallet -> _wallet_spend) —
        // chekda "Olib qolindi" va "Qoldi" shuni hisobga olishi shart.
        // Busiz chek balansni sarfsiz, oshirib ko'rsatib qo'yardi.
        const kurs = this.felizaHamyonKurs || 1;
        olindi += this.felizaHamyonSum / kurs;

        if (boredi < 0) {
            boredi = 0;       // manfiy qoldiq bo'lishi mumkin emas
        }
        const qoldi = boredi + qoshildi - olindi;
        return {
            boredi: pul(boredi),
            qoshildi: pul(qoshildi),
            olindi: pul(olindi),
            qoldi: pul(qoldi < 0 ? 0 : qoldi),
        };
    },
});
