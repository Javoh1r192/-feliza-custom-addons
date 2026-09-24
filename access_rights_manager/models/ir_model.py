# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class ir_model(models.Model):
    _inherit = 'ir.model'

    abstract = fields.Boolean('Abstract', readonly=True, help="Indicates if the model is abstract.")

    def name_get(self):
        """Custom name_get to include technical name if context key 'is_access_rights' is True."""
        res = super().name_get()
        if self._context.get('is_access_rights'):
            res = [(model.id, "{} ({})".format(model.name, model.model)) for model in self]
        return res


class IrModelField(models.Model):
    _inherit = 'ir.model.fields'

    def name_get(self):
        """Custom name_get to include field description and model if context key 'is_access_rights' is True."""
        res = super().name_get()
        if self._context.get('is_access_rights'):
            res = [(field.id, "{} => {} ({})".format(field.field_description, field.name, field.model_id.model)) for field in self]
        return res
