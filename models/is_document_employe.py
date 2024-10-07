# -*- coding: utf-8 -*-
from odoo import api, fields, models
import datetime


class is_type_document(models.Model):
    _name='is.type.document'
    _description = "Type de document"
    _order='name'

    name = fields.Char('Type de document', required=True)


class is_document_employe(models.Model):
    _name='is.document.employe'
    _description = "Documents du personnel"
    _order='employe_id'

    employe_id       = fields.Many2one('hr.employee', 'Employé'              , required=True)
    date_fin         = fields.Date("Date de fin"                             , required=True)
    type_document_id = fields.Many2one('is.type.document', 'Type de document', required=True)
    piece_jointe_ids = fields.Many2many('ir.attachment', 'is_document_employe_attachment_rel', 'document_id', 'attachment_id', 'Pièces jointes')
