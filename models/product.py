# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_type_prestation_id = fields.Many2one('is.type.prestation', 'Type de prestation')
