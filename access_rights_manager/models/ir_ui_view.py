from odoo import models, SUPERUSER_ID, _
from odoo.tools.translate import _
import ast


class ir_ui_view(models.Model):
    _inherit = 'ir.ui.view'

    def _postprocess_tag_field(self, node, name_manager, node_info):
        super()._postprocess_tag_field(node, name_manager, node_info)
        try:
            hide_field_obj = self.env['hide.field'].sudo()

            if node.tag == 'field' or node.tag == 'label':
                for hide_field in hide_field_obj.search(
                        [('access_rights_management_id.company_ids', 'in', self.env.company.id),
                         ('model_id.model', '=', name_manager.model._name), ('access_rights_management_id.active', '=', True),
                         ('access_rights_management_id.user_ids', 'in', self._uid)]):
                    for field_id in hide_field.field_id:
                        # print(node.get('name'), '\n')
                        if (node.tag == 'field' and node.get('name') == field_id.name) or (
                                node.tag == 'label' and 'for' in node.attrib.keys() and node.attrib[
                            'for'] == field_id.name):
                            # if node.tag == 'field':
                            if hide_field.external_link:
                                options_dict = {}
                                if 'options' in node.attrib.keys():
                                    options_dict = ast.literal_eval(node.attrib['options'])
                                    options_dict.update({"no_edit": True, "no_create": True, "no_open": True})
                                    node.attrib['options'] = str(options_dict)
                                else:
                                    node.attrib['options'] = str({"no_edit": True, "no_create": True, "no_open": True})
                                # node.attrib.update({'can_create': 'false', 'can_write': 'false','no_open':'true'})
                            if hide_field.invisible:
                                node_info['invisible'] = True
                                node.set('invisible', '1')
                            if hide_field.readonly:
                                node_info['readonly'] = True
                                node.set('readonly', '1')
                                node.set('force_save', '1')
                            if hide_field.required:
                                node_info['required'] = True
                                node.set('required', '1')
        except Exception:
            pass

    def _postprocess_tag_button(self, node, name_manager, node_info):
        # Hide Any Button
        postprocessor = getattr(super(ir_ui_view, self), '_postprocess_tag_button', False)
        if postprocessor:
            super(ir_ui_view, self)._postprocess_tag_button(node, name_manager, node_info)

        hide = None
        hide_button_obj = self.env['hide.view.nodes']
        hide_button_ids = hide_button_obj.sudo().search(
            [('access_rights_management_id.company_ids', 'in', self.env.company.id),
             ('model_id.model', '=', name_manager.model._name), ('access_rights_management_id.active', '=', True),
             ('access_rights_management_id.user_ids', 'in', self._uid)])

        btn_store_model_nodes_ids = hide_button_ids.mapped('btn_store_model_nodes_ids')
        if btn_store_model_nodes_ids:
            for btn in btn_store_model_nodes_ids:
                if btn.attribute_name == node.get('name'):
                    hide = [btn]
                    break
        if hide:
            node.set('invisible', '1')
            if 'attrs' in node.attrib.keys() and node.attrib['attrs']:
                del node.attrib['attrs']
            node_info['invisible'] = True

        return None

    def _postprocess_tag_page(self, node, name_manager, node_info):
        # Hide Any Notebook Page
        postprocessor = getattr(super(ir_ui_view, self), '_postprocess_tag_page', False)
        if postprocessor:
            super(ir_ui_view, self)._postprocess_tag_page(node, name_manager, node_info)

        hide = None
        hide_tab_obj = self.env['hide.view.nodes']
        hide_tab_ids = hide_tab_obj.sudo().search([('access_rights_management_id.company_ids', 'in', self.env.company.id),
                                                   ('model_id.model', '=', name_manager.model._name),
                                                   ('access_rights_management_id.active', '=', True),
                                                   ('access_rights_management_id.user_ids', 'in', self._uid)])
        page_store_model_nodes_ids = hide_tab_ids.mapped('page_store_model_nodes_ids')
        if page_store_model_nodes_ids:

            for tab in page_store_model_nodes_ids:
                attribute_string = tab.attribute_string
                if tab.lang_code != self.env.lang:
                    field = self.env['ir.ui.view']._fields['arch_db']
                    translation_dictionary = field.get_translation_dictionary(
                        self.with_context(lang=tab.lang_code).arch_db,
                        {self.env.lang: self.with_context(lang=self.env.lang)['arch_db']})
                    attribute_string = translation_dictionary[attribute_string][self.env.lang]
                if attribute_string == node.get('string'):
                    hide = [tab]
                    break

        if hide:
            node.set('invisible', '1')
            if 'attrs' in node.attrib.keys() and node.attrib['attrs']:
                del node.attrib['attrs']

            node_info['invisible'] = True

        return None

    def _postprocess_tag_div(self, node, name_manager, node_info):
        # Hide Any Notebook Page
        postprocessor = getattr(super(ir_ui_view, self), '_postprocess_tag_div', False)
        if postprocessor:
            super(ir_ui_view, self)._postprocess_tag_page(node, name_manager, node_info)

        hide_button_obj = self.env['hide.view.nodes'].sudo()

        if name_manager.model._name == 'res.config.settings' and node.tag == 'app' and node.get('string'):
            for setting_tab in hide_button_obj.search([('access_rights_management_id.company_ids', 'in', self.env.company.id),
                                                       ('model_id.model', '=', name_manager.model._name),
                                                       ('access_rights_management_id.active', '=', True),
                                                       ('access_rights_management_id.user_ids', 'in', self._uid)]).mapped(
                'page_store_model_nodes_ids'):
                attribute_string = setting_tab.attribute_string
                if setting_tab.lang_code != self.env.lang:
                    field = self.env['ir.ui.view']._fields['arch_db']
                    translation_dictionary = field.get_translation_dictionary(
                        self.with_context(lang=setting_tab.lang_code).arch_db,
                        {self.env.lang: self.with_context(lang=self.env.lang)['arch_db']})
                    attribute_string = translation_dictionary[attribute_string][self.env.lang]
                if node.get('data-key') == setting_tab.attribute_name:
                    # if node.get('string') == attribute_string and node.get('data-key') == setting_tab.attribute_name:
                    node_info['invisible'] = True
                    node.set('invisible', '1')

        return None

            

