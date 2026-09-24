from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.utils import ensure_db
from odoo.addons.web.controllers.home import Home as WebHome
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

class Home(WebHome):

    @http.route()
    def web_client(self, s_action=None, **kw):
        ensure_db()
        user = request.env.user.browse(request.session.uid)

        debug_param = kw.get('debug')
        if debug_param not in ('0', None, ''):
            cids = request.httprequest.cookies.get('cids') and \
                   int(request.httprequest.cookies.get('cids').split('-')[0]) or \
                   request.env.company.id

            access_right_management = request.env['access.rights.management'].sudo().search([
                ('active', '=', True),
                ('company_ids', 'in', cids),
                ('disable_developer_mode', '=', True),
                ('user_ids', 'in', user.id)
            ], limit=1)

            if access_right_management:
                current_url = request.httprequest.url
                parsed = urlparse(current_url)
                query = parse_qs(parsed.query)
                query['debug'] = '0'
                new_query = urlencode(query, doseq=True)
                new_url = urlunparse(parsed._replace(query=new_query))
                return request.redirect(new_url)

        return super().web_client(s_action, **kw)

class AccessRightsController(http.Controller):

    @http.route('/access_rights/check_restrictions', type='jsonrpc', auth='user')
    def check_restrictions(self, user_id, model_name=None):
        """Check both global and model-specific restrictions"""
        env = request.env
        cid = request.httprequest.cookies.get('cids') and int(request.httprequest.cookies.get('cids').split('-')[
                                                                  0]) or env.company.id
        global_restrictions = env['access.rights.management'].sudo().search([
            ('user_ids', 'in', [user_id]),
            ('company_ids', 'in', cid),
            ('active', '=', True)
        ])

        disable_export = any(global_restrictions.mapped('disable_export'))
        disable_archive = any(global_restrictions.mapped('disable_archive'))

        if model_name:
            model_restrictions = env['remove.action'].sudo().search([
                ('model_id.model', '=', model_name),
                ('access_rights_management_id.user_ids', 'in', [user_id]),
                ('access_rights_management_id.company_ids', 'in', cid),
                ('access_rights_management_id.active', '=', True)
            ])

            if model_restrictions:
                disable_export = any(model_restrictions.mapped('restrict_export')) or disable_export
                disable_archive = any(model_restrictions.mapped('restrict_archive')) or disable_archive

        return {
            'disable_export': disable_export,
            'disable_archive': disable_archive,
        }
