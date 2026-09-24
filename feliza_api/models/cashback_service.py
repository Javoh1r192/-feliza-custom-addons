from odoo import models
from typing import List

import logging
from operator import itemgetter

_logger = logging.getLogger(__name__)



class CashbackApiService(models.AbstractModel):
    _name = "feliza.cashback.api.service"
    _description = "Cashback API Service"

    def cashback(self, externalId):
        cards = self.env["loyalty.card"].sudo().search([
            ("partner_id", "=", externalId)
        ])

        total_points = sum(cards.mapped("points"))

        return {"success": True, "message": "success", "data": total_points}

    def history(self, externalId):
        cards = self.env["loyalty.card"].sudo().search([
            ("partner_id", "=", externalId)
        ])

        if not cards:
            return {"success": True, "message": "success", "data": []}

        history = self.env["loyalty.history"].sudo().search([
            ("card_id", "in", cards.ids)
        ], order="create_date desc")
        if not cards:
            return {"success": True, "message": "success", "data": []}

        result = []

        for item in history:
            result.append({
                "date": item.create_date,
                "description": item.description,
                "earned": item.issued,
                "used": item.used
            })

        return {"success": True, "message": "success", "data": result}