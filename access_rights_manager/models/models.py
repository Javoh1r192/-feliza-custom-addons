from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, AccessError
from odoo.tools.safe_eval import safe_eval
from lxml import etree
import ast

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)

        access_mgmt = self.env['access.rights.management'].sudo()
        readonly_rule = access_mgmt.search([
            ('company_ids', 'in', self.env.company.id),
            ('active', '=', True),
            ('user_ids', 'in', self.env.user.id),
            ('readonly', '=', True),
        ])
        model_rules = self.env['remove.action'].sudo().search([
            ('access_rights_management_id.company_ids', 'in', self.env.company.id),
            ('access_rights_management_id.user_ids', 'in', self.env.user.id),
            ('access_rights_management_id.active', '=', True),
            ('model_id.model', '=', self._name),
        ])
        mgmt_rules = access_mgmt.search([
            ('company_ids', 'in', self.env.company.id),
            ('user_ids', 'in', self.env.user.id),
            ('active', '=', True),
        ])

        hide_fields = self.env['hide.field'].sudo().search([
            ('access_rights_management_id.company_ids', 'in', self.env.company.id),
            ('model_id.model', '=', self._name),
            ('access_rights_management_id.active', '=', True),
            ('access_rights_management_id.user_ids', 'in', self.env.user.id),
        ])
        hide_nodes = self.env['hide.view.nodes'].sudo().search([
            ('access_rights_management_id.company_ids', 'in', self.env.company.id),
            ('model_id.model', '=', self._name),
            ('access_rights_management_id.active', '=', True),
            ('access_rights_management_id.user_ids', 'in', self.env.user.id),
        ])

        for view_type in ('form', 'list'):
            if view_type not in res['views']:
                continue
            view = res['views'][view_type]

            if readonly_rule:
                view['arch'] = self._update_view_permissions(
                    view.get('arch', ''), create='false', edit='false', delete='false', import_enabled='false'
                )
            else:
                create = 'true'
                edit = 'true'
                delete = 'true'
                duplicate = 'true'
                imp = 'true'
                for rule in model_rules:
                    if rule.restrict_create:    create = 'false'
                    if rule.restrict_edit:      edit = 'false'
                    if rule.restrict_delete:    delete = 'false'
                    if rule.restrict_duplicate: duplicate = 'false'
                    if rule.restrict_import:    imp = 'false'
                if mgmt_rules.filtered('disable_import'): imp = 'false'
                if mgmt_rules.filtered('disable_delete'): delete = 'false'
                view['arch'] = self._update_view_permissions(
                    view.get('arch', ''), create=create, edit=edit, delete=delete,
                    duplicate=duplicate, import_enabled=imp
                )

            rem = self.env['remove.action'].sudo().search([
                ('access_rights_management_id.company_ids', 'in', self.env.company.id),
                ('access_rights_management_id', 'in', self.env.user.access_rights_management_ids.ids),
                ('model_id.model', '=', self._name),
            ])
            server_ids = rem.mapped('server_action_ids.action_id').ids
            print_ids = rem.mapped('report_action_ids.action_id').ids
            toolbar = view.setdefault('toolbar', {})
            if toolbar.get('action'):
                toolbar['action'] = [a for a in toolbar['action'] if a['id'] not in server_ids]
            if toolbar.get('print'):
                toolbar['print'] = [p for p in toolbar['print'] if p['id'] not in print_ids]

            arch_str = view.get('arch')
            if arch_str:
                try:
                    doc = etree.XML(arch_str)
                except Exception:
                    continue
                for rule in hide_fields:
                    for fld in rule.field_id:
                        xpath_expr = f"//field[@name='{fld.name}'] | //label[@for='{fld.name}']"
                        for node in doc.xpath(xpath_expr):
                            if rule.external_link:
                                opts = node.get('options') or '{}'
                                opts_dict = ast.literal_eval(opts)
                                opts_dict.update({'no_edit': True, 'no_create': True, 'no_open': True})
                                node.set('options', str(opts_dict))
                            if rule.invisible:
                                node.set('invisible', '1')
                            if rule.readonly:
                                node.set('readonly', '1')
                                node.set('force_save', '1')
                            if rule.required:
                                node.set('required', '1')
                for rule in hide_nodes:
                    for btn in rule.btn_store_model_nodes_ids:
                        for n in doc.xpath(f"//button[@name='{btn.attribute_name}']"):
                            n.set('invisible', '1')
                            n.attrib.pop('attrs', None)
                    for pg in rule.page_store_model_nodes_ids:
                        for n in doc.xpath(f"//page[@string='{pg.attribute_string}']"):
                            n.set('invisible', '1')
                            n.attrib.pop('attrs', None)
                    for dv in rule.page_store_model_nodes_ids:
                        for n in doc.xpath(f"//div[@data-key='{dv.attribute_name}']"):
                            n.set('invisible', '1')
                            n.attrib.pop('attrs', None)
                view['arch'] = etree.tostring(doc, encoding='unicode')

        return res

    def _update_view_permissions(self, arch_str, create='true', edit='true', delete='true', duplicate='true',
                                 import_enabled='true'):
        if not arch_str:
            return arch_str
        try:
            doc = etree.XML(arch_str)
        except Exception:
            return arch_str
        doc.attrib.update({
            'create': create,
            'edit': edit,
            'delete': delete,
            'duplicate': duplicate,
            'import': import_enabled,
        })
        return etree.tostring(doc, encoding='unicode')


    @api.model
    def load_views(self, views, options=None):
        actions_and_prints = []
        for access in self.env['remove.action'].sudo().search([('access_rights_management_id.company_ids', 'in', self.env.company.id),
                                                        ('access_rights_management_id', 'in',
                                                         self.env.user.access_rights_management_ids.ids),
                                                        ('model_id.model', '=', self._name)]):
            actions_and_prints = actions_and_prints + access.mapped('report_action_ids.action_id').ids
            actions_and_prints = actions_and_prints + access.mapped('server_action_ids.action_id').ids

        res = super(BaseModel, self).load_views(views, options=options)

        if 'fields_views' in res.keys():
            for view in ['list', 'form']:
                if view in res['fields_views'].keys():
                    if 'toolbar' in res['fields_views'][view].keys():
                        if 'print' in res['fields_views'][view]['toolbar'].keys():
                            prints = res['fields_views'][view]['toolbar']['print'][:]
                            for pri in prints:
                                if pri['id'] in actions_and_prints:
                                    res['fields_views'][view]['toolbar']['print'].remove(pri)
                        if 'print' in res['fields_views'][view]['toolbar'].keys():
                            action = res['fields_views'][view]['toolbar']['action'][:]
                            for act in action:
                                if act['id'] in actions_and_prints:
                                    res['fields_views'][view]['toolbar']['action'].remove(act)
        return res

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id, view_type, **options)

        if not res.get('arch'):
            return res

        try:
            doc = etree.XML(res['arch'])
        except Exception:
            return res

        access_management_obj = self.env['access.rights.management'].sudo()

        readonly_access_id = access_management_obj.search([
            ('company_ids', 'in', self.env.company.id),
            ('active', '=', True),
            ('user_ids', 'in', self.env.user.id),
            ('readonly', '=', True)
        ])

        access_model_recs = self.env['remove.action'].sudo().search([
            ('access_rights_management_id.company_ids', 'in', self.env.company.id),
            ('access_rights_management_id.user_ids', 'in', self.env.user.id),
            ('access_rights_management_id.active', '=', True),
            ('model_id.model', '=', res['model'])
        ])

        access_rights_management_ids = access_management_obj.search([
            ('company_ids', 'in', self.env.company.id),
            ('user_ids', 'in', self.env.user.id),
            ('active', '=', True)
        ])

        if view_type == 'form':
            access_rights_management_id = access_management_obj.search([
                ('company_ids', 'in', self.env.company.id),
                ('user_ids', 'in', self.env.user.id),
                ('active', '=', True),
                ('hide_chatter', '=', True)
            ], limit=1)
            if access_rights_management_id:
                for chatter in doc.xpath("//chatter"):
                    chatter.getparent().remove(chatter)
            else:
                rule_hide = access_rights_management_ids.hide_chatter_ids.filtered(lambda l:l.model_id.model == self._name and l.hide_chatter)
                if rule_hide:
                    for chatter in doc.xpath("//chatter"):
                        chatter.getparent().remove(chatter)

        if readonly_access_id:
            if view_type in ('form', 'list', 'kanban'):
                doc.attrib.update({
                    'create': 'false',
                    'delete': 'false',
                    'edit': 'false',
                    'import': 'false'
                })
        else:
            if access_model_recs or access_rights_management_ids:
                create = 'true'
                edit = 'true'
                delete = 'true'
                duplicate = 'true'
                import_enabled = 'true'

                for access_model in access_model_recs:
                    if access_model.restrict_create:
                        create = 'false'
                    if access_model.restrict_edit:
                        edit = 'false'
                    if access_model.restrict_delete:
                        delete = 'false'
                    if access_model.restrict_duplicate:
                        duplicate = 'false'
                    if access_model.restrict_import:
                        import_enabled = 'false'

                if access_rights_management_ids.filtered('disable_import'):
                    import_enabled = 'false'
                if access_rights_management_ids.filtered('disable_delete'):
                    delete = 'false'

                if view_type in ('form', 'list', 'kanban'):
                    doc.attrib.update({
                        'create': create,
                        'delete': delete,
                        'edit': edit,
                        'duplicate': duplicate,
                        'import': import_enabled
                    })

        res['arch'] = etree.tostring(doc, encoding='unicode').replace('&amp;quot;', '&quot;')
        return res


    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        access_management_obj = self.env['access.rights.management'].sudo()

        readonly_access_id = access_management_obj.search([
            ('company_ids', 'in', self.env.company.id),
            ('active', '=', True),
            ('user_ids', 'in', self.env.user.id),
            ('readonly', '=', True)
        ])

        access_model_recs = self.env['remove.action'].sudo().search([
            ('access_rights_management_id.company_ids', 'in', self.env.company.id),
            ('access_rights_management_id.user_ids', 'in', self.env.user.id),
            ('access_rights_management_id.active', '=', True),
            ('model_id.model', '=', self._name)
        ])

        access_rights_management_ids = access_management_obj.search([
            ('company_ids', 'in', self.env.company.id),
            ('user_ids', 'in', self.env.user.id),
            ('active', '=', True)
        ])

        if view_type == 'form':
            access_rights_management_id = access_management_obj.search([
                ('company_ids', 'in', self.env.company.id),
                ('user_ids', 'in', self.env.user.id),
                ('active', '=', True),
                ('hide_chatter', '=', True)
            ], limit=1)
            if access_rights_management_id:
                for chatter in arch.xpath("//chatter"):
                    chatter.getparent().remove(chatter)
            else:
                rule_hide = access_rights_management_ids.hide_chatter_ids.filtered(
                    lambda l: l.model_id.model == self._name and l.hide_chatter)
                if rule_hide:
                    for chatter in arch.xpath("//chatter"):
                        chatter.getparent().remove(chatter)

        if readonly_access_id:
            if view_type in ('form', 'list', 'kanban'):
                arch.attrib.update({'create': 'false', 'delete': 'false', 'edit': 'false', 'import': 'false'})
        else:
            if access_model_recs or access_rights_management_ids:
                create = 'true'
                edit = 'true'
                delete = 'true'
                duplicate = 'true'
                import_enabled = 'true'

                for access_model in access_model_recs:
                    if access_model.restrict_create:
                        create = 'false'
                    if access_model.restrict_edit:
                        edit = 'false'
                    if access_model.restrict_delete:
                        delete = 'false'
                    if access_model.restrict_duplicate:
                        duplicate = 'false'
                    if access_model.restrict_import:
                        import_enabled = 'false'

                if access_rights_management_ids.filtered('disable_import'):
                    import_enabled = 'false'

                if access_rights_management_ids.filtered('disable_delete'):
                    delete = 'false'
                if view_type in ('form', 'list', 'kanban'):
                    arch.attrib.update({
                        'create': create,
                        'delete': delete,
                        'edit': edit,
                        'duplicate': duplicate,
                        'import': import_enabled
                    })

        return arch, view


