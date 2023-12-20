# -*- coding: utf-8 -*-
from odoo import api, fields, models

class res_company(models.Model):
    _inherit = 'res.company'

    is_affacturage          = fields.Text('Affacturage')
    is_conditions_generales = fields.Text('Conditions générales')
    is_sms_account  = fields.Char('SMS account')
    is_sms_login    = fields.Char('SMS login')
    is_sms_password = fields.Char('SMS password')
    is_sms_from     = fields.Char('SMS from')
    is_sms_message  = fields.Text('SMS message')
    is_sms_mobile   = fields.Char('SMS Mobile de test')


