import logging
from datetime import timedelta

import requests

from odoo import models

# Feliza webhook hujjati: "ISO-8601, local, no offset" (Asia/Tashkent, UTC+5).
# Odoo write_date/create_date har doim UTC (naive) saqlanadi.
TASHKENT_OFFSET = timedelta(hours=5)


def to_feliza_datetime(dt):
    """UTC (naive) datetime'ni Feliza kutayotgan formatga o'giradi:
    Asia/Tashkent mahalliy vaqti, offset'siz ISO-8601 (masalan
    2026-08-15T14:30:00)."""
    if not dt:
        return None
    return (dt + TASHKENT_OFFSET).isoformat()

_logger = logging.getLogger(__name__)

# Qayta urinish jadvali (TZ'dagi 5s -> 30s -> 5daq -> 30daq -> 2soatga
# yaqinlashtirilgan) haqiqatda data/queue_job_function_data.xml faylidagi
# har bir queue.job.function yozuvida sozlanadi - bu yerda faqat izoh
# uchun saqlanadi.
RETRY_PATTERN = {1: 5, 2: 30, 3: 300, 4: 1800, 5: 7200}


class FelizaWebhookClient(models.AbstractModel):
    _name = "feliza.webhook.client"
    _description = "Feliza Webhook Client (Odoo -> Feliza)"

    def _get_api_key(self):
        api_key = self.env["ir.config_parameter"].sudo().get_param("feliza.webhook.api_key")
        if not api_key:
            raise ValueError(
                "feliza.webhook.api_key sozlanmagan. "
                "Settings > Technical > Parameters > System Parameters orqali qo'shing."
            )
        return api_key

    def _get_base_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("feliza.webhook.base_url")
        if not base_url:
            raise ValueError(
                "feliza.webhook.base_url sozlanmagan. "
                "Settings > Technical > Parameters > System Parameters orqali qo'shing "
                "(production: https://felizabackend.uz/api/odoo/webhook). "
                "Local/staging muhitda bu ataylab bo'sh qoldirilishi kerak - "
                "aks holda test yozuvlar production Feliza serveriga yuboriladi."
            )
        return base_url.rstrip("/")

    def post(self, path, payload):
        """Feliza webhook endpointiga sinxron POST yuboradi va javobni
        qaytaradi. Xato bo'lsa exception ko'taradi.

        Bu metod har doim `.with_delay()` orqali navbatga qo'yiladigan
        metod ICHIDAN chaqirilishi kerak (masalan
        `product.product._feliza_send_upsert`) - shunda xato bo'lsa
        queue_job data/queue_job_function_data.xml'da shu metod uchun
        sozlangan retry_pattern bo'yicha avtomatik qayta urinadi va
        asosiy write()/create() tranzaksiyasi Feliza serveri sekin/o'chiq
        bo'lgan taqdirda ham bloklanib qolmaydi.
        """
        api_key = self._get_api_key()
        url = f"{self._get_base_url()}{path}"
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

        _logger.info("Feliza webhook -> %s payload=%s", url, payload)

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        body = None
        if response.content:
            try:
                body = response.json()
            except ValueError:
                body = response.text

        _logger.info("Feliza webhook <- %s [%s] %s", url, response.status_code, body)
        return body
