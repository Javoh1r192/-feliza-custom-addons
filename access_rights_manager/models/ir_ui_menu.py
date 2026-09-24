from odoo import fields, models, api, _
from odoo.http import request
import copy
class ir_ui_menu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def load_menus(self, debug):
        orig_menus = super(ir_ui_menu, self).load_menus(debug)
        menus = copy.deepcopy(orig_menus)

        user = self.env.user
        cids = request.httprequest.cookies.get('cids') and int(
            request.httprequest.cookies.get('cids').replace(',', '-').split('-')[0]
        ) or self.env.company.id

        hide_menu_vals = user.access_rights_management_ids.filtered(
            lambda line: cids in line.company_ids.ids
        ).mapped('hide_menu_ids.menu_id')

        hidden_ids = set()
        for h in hide_menu_vals:
            hidden_ids.add(int(h) if isinstance(h, (int, str)) and str(h).isdigit() else int(getattr(h, 'id', h)))

        new_menus = {}
        for mid, mval in menus.items():
            if mid in hidden_ids:
                continue
            entry = copy.deepcopy(mval)
            if entry.get('children'):
                entry['children'] = [c for c in entry['children'] if c not in hidden_ids]
            new_menus[mid] = entry

        removed = True
        while removed:
            removed = False
            for mid, menu in list(new_menus.items()):
                if not menu.get('children') and not menu.get('action_model') and not menu.get('action_id'):
                    new_menus.pop(mid, None)
                    for m2 in new_menus.values():
                        if m2.get('children'):
                            m2['children'] = [c for c in m2['children'] if c != mid]
                    removed = True

        return new_menus

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ir_ui_menu, self).create(vals_list)
        menu_item_obj = self.env['menu.item']
        for record in res:
            menu_item_obj.create({'name':record.display_name,'menu_id':record.id})
        return res

    def unlink(self):
        menu_item_obj = self.env['menu.item']
        for record in self:
            menu_item_obj.search([('menu_id','=',record.id)]).unlink()
        return super(ir_ui_menu, self).unlink()

