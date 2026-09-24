from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from odoo import SUPERUSER_ID
from odoo.api import Environment

from odoo.addons.fastapi.dependencies import odoo_env

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def validate_api_key(
        api_key: Annotated[str | None, Depends(api_key_header)],
        env: Annotated[Environment, Depends(odoo_env)],
):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        )

    expected = (
        env["ir.config_parameter"]
        .with_user(SUPERUSER_ID)
        .get_param("feliza.api.key")
    )

    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    return True