from odoo import models, fields

from ..routers import api_router
from ..routers import product_router
from ..routers import customer_router
from ..routers import cashback_router
from ..routers import order_router
from ..routers import operator_router

class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app = fields.Selection(
        selection_add=[
            ("feliza", "Feliza API"),
        ],
        ondelete={"feliza": "cascade"},
    )

    def _get_fastapi_routers(self):
        if self.app == "feliza":
            return [
                api_router,
                product_router,
                customer_router,
                cashback_router,
                order_router,
                operator_router
            ]

        return super()._get_fastapi_routers()