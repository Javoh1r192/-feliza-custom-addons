from odoo import models, api, tools, _
from odoo.tools.safe_eval import safe_eval
from odoo.tools import config
from odoo.fields import Domain
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class IrRule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    @tools.conditional(
        'xml' not in config['dev_mode'],
        tools.ormcache(
            'self.env.uid',
            'self.env.su',
            'model_name',
            'mode',
            'tuple(self._compute_domain_context_values())'
        ),
    )
    def _compute_domain(self, model_name, mode="read"):
        original_domain = super(IrRule, self)._compute_domain(model_name, mode=mode)

        if self.env.su and original_domain == [(1, '=', 1)]:
            return original_domain

        model = self.env[model_name]
        user = self.env.user
        company = self.env.company

        domain_rules = self.env['user.domain.access'].sudo().search([
            ('access_rights_management_id.user_ids', 'in', user.ids),
            ('model_name', '=', model_name),
            ('access_rights_management_id.company_ids', 'in', company.id),
            ('access_rights_management_id.active', '=', True)
        ])
        if model_name == 'account.account':
            _logger.info("User: %s, Company: %s, Domain Rules: %s", user, company.id, domain_rules)

        eval_context = {
            'user': user,
            'current_company': company,
            'context': self.env.context,
            'uid': user.id,
            'time': datetime.now(),
            '_': _,
        }

        custom_domain_objs = []
        for rule in domain_rules:
            if not rule.assignment_domain:
                continue
            try:
                dom_eval = safe_eval(
                    rule.assignment_domain,
                    context=eval_context,
                    mode="eval"
                )
            except Exception as e:
                _logger.error(
                    "Failed to safe_eval assignment_domain for rule ID %s (User: %s, Model: %s): %s",
                    rule.id, user.id, model_name, e
                )
                continue

            _logger.debug("dom_eval: %s", dom_eval)

            if isinstance(dom_eval, Domain):
                dom_obj = dom_eval
            elif isinstance(dom_eval, (list, tuple)):
                try:
                    dom_obj = Domain(dom_eval)
                except Exception as e:
                    _logger.error(
                        "Invalid domain structure in rule ID %s (User: %s, Model: %s): %s — %s",
                        rule.id, user.id, model_name, dom_eval, e
                    )
                    continue
            else:
                _logger.error(
                    "assignment_domain for rule ID %s did not evaluate to a domain (got %s). Skipping.",
                    rule.id, type(dom_eval)
                )
                continue

            custom_domain_objs.append(dom_obj)

        if not custom_domain_objs:
            if isinstance(original_domain, list):
                return Domain(original_domain)
            return original_domain

        if isinstance(original_domain, list):
            original_domain_obj = Domain(original_domain)
        else:
            original_domain_obj = original_domain

        if original_domain == [(1, '=', 1)]:
            final_domain_obj = Domain.AND(custom_domain_objs) if len(custom_domain_objs) > 1 else custom_domain_objs[0]
        else:
            final_domain_obj = Domain.AND([original_domain_obj] + custom_domain_objs)

        try:
            final_domain_obj = final_domain_obj.optimize(model)
        except Exception:
            _logger.debug("Domain.optimize() failed for model %s; continuing without optimize()", model_name)

        return final_domain_obj
