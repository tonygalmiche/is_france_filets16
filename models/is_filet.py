# -*- coding: utf-8 -*-
from odoo import api, fields, models
import datetime


_POSITIONS = [
    ('depot-dijon'  , u'Dépôt Dijon'),
    ('depot-pexiora', u'Dépôt Pexiora'),
    ('camionnette'  , u'Camionnette'),
    ('chantier'     , u'Chantier'),
]

_ETAT_FILET = [
    ('conforme' , u'Conforme'),
    ('a-reparer', u'A réparer'),
    ('hs'       , u'HS'),
]

class is_filet(models.Model):
    _name='is.filet'
    _description = "is_filet"
    _order='name desc'

    name = fields.Char(u"N°Filet", readonly=True)
    type_filet = fields.Selection([
        ('simple'     , u'Filet simple'),
        ('pare-gravat', u'Filet doublé pare-gravât'),
    ], 'Type de filet', default='simple',required=True)
    dimensions       = fields.Char(u"Dimensions", required=True)
    fabriquant       = fields.Char(u"Fabriquant", required=True)
    num_serie        = fields.Char(u"N°de série", required=True)
    date_fabrication = fields.Date(u"Date de fabrication", required=True)
    prix_achat       = fields.Float(u"Prix d'achat", digits=(14,2))
    etat_filet       = fields.Selection(_ETAT_FILET, u'État du filet'   , compute='onchange_mouvement_ids', readonly=True, store=True)
    position         = fields.Selection(_POSITIONS, u'Position actuelle', compute='onchange_mouvement_ids', readonly=True, store=True)
    latitude         = fields.Char(u"GPS - Latitude"                    , compute='onchange_mouvement_ids', readonly=True, store=True)
    longitude        = fields.Char(u"GPS - Longitude"                   , compute='onchange_mouvement_ids', readonly=True, store=True)
    depuis_le        = fields.Datetime(u"Depuis le"                     , compute='onchange_mouvement_ids', readonly=True, store=True)
    effectue_par_id  = fields.Many2one('res.users', 'Effectué par'      , compute='onchange_mouvement_ids', readonly=True, store=True)
    chantier_id      = fields.Many2one('is.chantier', u'Chantier'       , compute='onchange_mouvement_ids', readonly=True, store=True)
    mouvement_ids = fields.One2many('is.filet.mouvement', 'filet_id', u"Mouvements")


    def get_type_filet_selection(self):
        """Retourne pour l'application mobile, la liste de selection du champ type_filet"""
        res = self.env["is.filet"]._fields["type_filet"].selection
        return res


    # @api.model
    # def create(self, vals):
    #     vals['name'] = self.env['ir.sequence'].next_by_code('is.filet')
    #     res = super(is_filet, self).create(vals)
    #     return res


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.filet')
        return super().create(vals_list)


    @api.depends('mouvement_ids')
    def onchange_mouvement_ids(self):
        for obj in self:
            depuis_le=False
            for m in obj.mouvement_ids:
                if not depuis_le:
                    depuis_le=m.name
                if m.name>=depuis_le:
                    position    = m.position
                    depuis_le   = m.name
                    chantier_id = m.chantier_id.id
                    etat_filet  = m.etat_filet
                    latitude    = m.latitude
                    longitude   = m.longitude
                    effectue_par_id = m.create_uid
            if depuis_le:
                obj.position    = position
                obj.depuis_le   = depuis_le
                obj.chantier_id = chantier_id
                obj.etat_filet  = etat_filet
                obj.latitude    = latitude
                obj.longitude   = longitude
                obj.effectue_par_id = effectue_par_id


    def get_nb_filets(self,chantier_id):
        """Retourne pour l'application mobile, le nombre de filets pour un chantier"""
        ids = self.env['is.filet'].search([('chantier_id','=',chantier_id)])
        return len(ids)


class is_filet_mouvement(models.Model):
    _name='is.filet.mouvement'
    _description = "is_filet_mouvement"
    _order='name desc'

    filet_id    = fields.Many2one('is.filet', 'Filet', required=True, ondelete='cascade',index=True)
    name        = fields.Datetime(u"Heure du mouvement", default=lambda self: fields.Datetime.now(),required=True)
    position    = fields.Selection(_POSITIONS, 'Position',required=True)
    latitude    = fields.Char(u"GPS - Latitude")
    longitude   = fields.Char(u"GPS - Longitude")
    etat_filet  = fields.Selection(_ETAT_FILET, u'État du filet')
    chantier_id = fields.Many2one('is.chantier', u'Chantier')

    type_filet       = fields.Selection(related='filet_id.type_filet')
    dimensions       = fields.Char(related='filet_id.dimensions')
    fabriquant       = fields.Char(related='filet_id.fabriquant')
    num_serie        = fields.Char(related='filet_id.num_serie')
    date_fabrication = fields.Date(related='filet_id.date_fabrication')



    def get_position_selection(self):
        """Retourne pour l'application mobile, la liste de selection du champ position"""
        return _POSITIONS


    def get_etat_filet_selection(self):
        """Retourne pour l'application mobile, la liste de selection du champ etat_filet"""
        # Methode en accèdant directement au champ sans passer par la liste _ETAT_FILET
        res = self.env["is.filet.mouvement"]._fields["etat_filet"].selection
        return res





