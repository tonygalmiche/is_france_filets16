# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_account_invoice_line_id = fields.Integer('Lien entre account_invoice_line et account_move_line pour la migration')

