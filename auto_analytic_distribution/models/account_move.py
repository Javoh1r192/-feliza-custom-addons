# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Jurnal o'zgarganda analitik hisobni avtomatik to'ldirish"""
        res = super()._onchange_journal_id()
        
        if self.journal_id and self.journal_id.default_analytic_distribution:
            # Har bir qatorga analitik distribyutsiyani qo'shish
            for line in self.line_ids:
                # Faqat debet yoki kredit bo'lgan qatorlarga
                if (line.debit or line.credit) and not line.analytic_distribution:
                    line.analytic_distribution = self.journal_id.default_analytic_distribution
        
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    @api.model_create_multi
    def create(self, vals_list):
        """Yangi qator yaratilganda jurnaldan analitik hisobni olish"""
        for vals in vals_list:
            # Agar analitik distribyutsiya kiritilmagan bo'lsa
            if not vals.get('analytic_distribution'):
                journal = None
                
                # Move yoki journal_id dan olish
                if vals.get('move_id'):
                    move = self.env['account.move'].browse(vals['move_id'])
                    journal = move.journal_id
                elif vals.get('journal_id'):
                    journal = self.env['account.journal'].browse(vals['journal_id'])
                
                # Jurnaldan default analitik distribyutsiyani olish
                if journal and journal.default_analytic_distribution:
                    # Faqat debet yoki kredit bo'lgan qatorlarga
                    if vals.get('debit', 0.0) != 0.0 or vals.get('credit', 0.0) != 0.0:
                        vals['analytic_distribution'] = journal.default_analytic_distribution
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Jurnal o'zgartirilganda analitik hisobni yangilash"""
        res = super().write(vals)
        
        # Agar jurnal o'zgartirilgan bo'lsa va analitik distribyutsiya bo'sh bo'lsa
        if 'journal_id' in vals:
            for line in self:
                if line.journal_id and line.journal_id.default_analytic_distribution:
                    if not line.analytic_distribution and (line.debit or line.credit):
                        line.analytic_distribution = line.journal_id.default_analytic_distribution
        
        return res
