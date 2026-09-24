/** @odoo-module */

/**
 * Umumiy yordamchi funksiyalar: mijozning cashback balansini Odoo'ning
 * o'z Loyalty ma'lumotlaridan (POS frontendiga allaqachon yuklangan
 * `loyalty.card` / `loyalty.reward` / `res.company`) hisoblash uchun.
 *
 * Bu yerda hech qanday alohida "hamyon" balansi saqlanmaydi — hammasi
 * to'g'ridan-to'g'ri native Loyalty modellaridan o'qiladi, shuning uchun
 * POS frontendida ko'rsatiladigan raqam har doim serverdagi haqiqiy
 * Loyalty ball balansi bilan bir xil bo'ladi.
 */

export function getWalletProgram(models) {
    const configs = models["pos.config"];
    const config = configs && configs.getFirst && configs.getFirst();
    const company = config && config.company_id;
    return (company && company.pos_wallet_loyalty_program_id) || null;
}

export function getWalletPointRate(models) {
    const program = getWalletProgram(models);
    if (!program) {
        return 1;
    }
    const reward = models["loyalty.reward"].find(
        (r) =>
            r.program_id &&
            r.program_id.id === program.id &&
            r.reward_type === "discount" &&
            r.discount_mode === "per_point"
    );
    return reward && reward.discount ? reward.discount : 1;
}

export function getWalletCard(models, partner) {
    const program = getWalletProgram(models);
    if (!program || !partner) {
        return null;
    }
    return (
        models["loyalty.card"].find(
            (c) =>
                c.partner_id &&
                c.partner_id.id === partner.id &&
                c.program_id &&
                c.program_id.id === program.id
        ) || null
    );
}

export function getWalletBalance(models, partner) {
    const card = getWalletCard(models, partner);
    const rate = getWalletPointRate(models);
    return card ? card.points * rate : 0;
}
