from odoo import models

import logging
from operator import itemgetter
from fastapi import HTTPException
import re

from ..schemas.response import PageResponse

_logger = logging.getLogger(__name__)



class CustomersApiService(models.AbstractModel):
    _name = "feliza.customers.api.service"
    _description = "Customers API Service"

    def page(self, page, size, phone=None, fullname=None, externalId=None):
        # registration_status hammasi uchun default "offline" (hali hech kim
        # saytda "registered" qilib belgilanmagan), shuning uchun bu maydon
        # bo'yicha filtrlash deyarli har doim 0 natija berardi. Haqiqiy
        # mijoz - telefon raqami bor partner (export_mapping.sql'dagi bilan
        # bir xil mezon). externalId aniq qidiruv - shu filtrdan qat'i nazar.
        if externalId:
            domain = [("id", "=", externalId)]
        else:
            domain = [("phone", "!=", False)]

            if phone:
                domain.append(("phone", "ilike", phone))

            if fullname:
                domain.append(("name", "ilike", fullname))

        total_elements = self.env["res.partner"].sudo().search_count(domain)
        if total_elements == 0:
            return {"success": True, "message": "success", "data": PageResponse.empty(page, size)}

        customers = self.env["res.partner"].sudo().search(
            domain,
            offset=(page - 1) * size,
            limit=size,
            order="id desc",
        )

        content = [
            {
                "externalId": customer.id,
                "fullname": customer.name or None,
                "phone": customer.phone or None,
                "birthDate": customer.birthdate or None,
                "registrationStatus": customer.registration_status or None
            }
            for customer in customers
        ]

        return {
            "success": True,
            "message": "success",
            "data": PageResponse.of(content, page, size, total_elements)
        }

    def create(self, req):
        customer = self.env['res.partner'].sudo().search([('phone', '=', req.phone)], limit=1)
        if not customer:
            customer = self.env['res.partner'].sudo().create({
                "name": req.fullname,
                "phone": req.phone,
                "birthdate": req.birthDate,
                "registration_status": "registered"
            })
        else:
            customer.write({
                "registration_status": "registered",
                "name": req.fullname,
                "birthdate": req.birthDate
            })
        return {"success": True, "message": "created", "data": customer.id}

    def update(self, req):
        customer = self.env['res.partner'].sudo().browse(req.externalId).exists()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        customer.write({
            "name": req.fullname if req.fullname else customer.name,
            "phone": req.phone if req.phone else customer.phone,
            "birthdate": req.birthDate if req.birthDate else customer.birthdate
        })
        return {"success": True, "message": "updated"}


    def by_phone(self, phone):
        if not phone:
            raise HTTPException(status_code=400, detail="Invalid phone number")

        if not re.fullmatch(r"^\+998\d{9}$", phone):
            raise HTTPException(status_code=400, detail="Invalid phone number")

        customer = self.env['res.partner'].sudo().search_read(
            domain=[('phone', '=', phone)],
            fields=['id', 'name', 'birthdate', 'registration_status']
        )

        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        data = {
            "externalId": customer[0]['id'],
            "fullname": customer[0]["name"] or None,
            "phone": phone or None,
            "birthDate": customer[0]['birthdate'] or None,
            "registrationStatus": customer[0]['registration_status'] or None
        }

        return {"success": True, "message": "success", "data": data}

    def profile(self, externalId):
        customer = self.env['res.partner'].sudo().browse(externalId).exists()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        data = {
            "externalId": customer.id,
            "fullname": customer.name or None,
            "phone": customer.phone or None,
            "birthDate": customer.birthdate or None,
            "registrationStatus": customer.registration_status or None
        }

        return {"success": True, "message": "success", "data": data}