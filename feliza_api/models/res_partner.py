import logging

from odoo import models, fields, api

from .feliza_webhook_client import to_feliza_datetime

_logger = logging.getLogger(__name__)

# Shu maydonlardan biri o'zgarsa - customer-updated webhooki yuboriladi.
TRACKED_PARTNER_FIELDS = {"name", "phone", "birthdate", "x_gender"}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    registration_status = fields.Selection(
        [
            ("offline", "Offline"),
            ("pending", "Pending"),
            ("registered", "Registered"),
            ("blocked", "Blocked"),
        ],
        string="Registration Status",
        default="offline",
        required=True,
        index=True,
    )
    birthdate = fields.Date(string="Birth Date", tracking=True)
    x_gender = fields.Selection(
        [("male", "Erkak"), ("female", "Ayol")],
        string="Jins",
        tracking=True,
    )

    def write(self, vals):
        result = super().write(vals)

        if TRACKED_PARTNER_FIELDS & set(vals.keys()):
            for partner in self:
                if partner._feliza_is_customer():
                    partner._feliza_push_customer_updated()

        return result

    # ---------------------------------------------------------------
    # Feliza webhook: customer-updated
    # ---------------------------------------------------------------

    def _feliza_is_customer(self):
        """Faqat haqiqiy (xarid qilgan yoki cashback kartasi bor) mijozlar
        uchun webhook yuboriladi - har bir yetkazib beruvchi/ichki
        kontaktning tahriri Feliza'ga jo'natilmasin."""
        self.ensure_one()
        if self.customer_rank > 0:
            return True
        return bool(
            self.env["loyalty.card"].sudo().search_count([("partner_id", "=", self.id)])
        )

    def _feliza_cashback_balance(self):
        self.ensure_one()
        cards = self.env["loyalty.card"].sudo().search([("partner_id", "=", self.id)])
        return sum(cards.mapped("points"))

    def _feliza_push_customer_updated(self):
        self.ensure_one()
        if self.registration_status != "registered":
            return
        self.with_delay(
            identity_key=f"feliza-customer-updated-{self.id}",
            description=f"Feliza customer-updated: partner {self.id}",
        )._feliza_send_customer_updated()

    def _feliza_send_customer_updated(self):
        self.ensure_one()
        payload = {
            "odoo_external_id": self.id,
            "phone": self.phone,
            "fullname": self.name,
            "birth_date": self.birthdate.isoformat() if self.birthdate else None,
            "gender": self.x_gender or None,
            "cashback_balance": self._feliza_cashback_balance(),
            "changed_at": to_feliza_datetime(self.write_date),
        }
        self.env["feliza.webhook.client"].post("/customer-updated", payload)