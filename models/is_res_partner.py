# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools
import datetime
import pytz


class is_res_partner(models.Model):
    _name='is.res.partner'
    _description = "is_res_partner"
    _order='parent_id,name'
    _auto = False

    parent_id  = fields.Many2one('res.partner', 'Société parent')
    name       = fields.Char('Contact')
    is_company = fields.Boolean('Société')
    street     = fields.Char('Rue')
    zip        = fields.Char('CP')
    city       = fields.Char('Ville')
    phone      = fields.Char('Téléphone')
    fax        = fields.Char('Fax')
    mobile     = fields.Char('Mobile')
    email      = fields.Char('Mail')
    website    = fields.Char('Site')
    function   = fields.Char('Fonction')
    is_type_partenaire = fields.Selection([
        ('Client'      , 'Client'),
        ('Prospect'    , 'Prospect'),
        ('Prescripteur', 'Prescripteur'),
    ], u'Type de partenaire')
    is_region_id           = fields.Many2one('is.region'          , u'Région')
    is_secteur_activite_id = fields.Many2one('is.secteur.activite', u"Secteur d'activité")

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, 'is_res_partner')
        cr.execute("""
            CREATE OR REPLACE view is_res_partner AS (
                select * 
                from (

                    select 
                        rp1.id,
                        rp1.parent_id,
                        rp1.name,
                        rp1.is_company,
                        rp1.street,
                        rp1.zip,
                        rp1.city,
                        rp1.phone,
                        rp1.fax,
                        rp1.mobile,
                        rp1.email,
                        rp1.website,
                        rp1.function,
                        rp2.is_type_partenaire,
                        rp2.is_region_id,
                        rp2.is_secteur_activite_id 
                    from res_partner rp1 inner join res_partner rp2 on rp1.parent_id=rp2.id
                    where rp1.parent_id is not null and rp1.active='t'

                    union

                    select 
                        id,
                        id as parent_id,
                        '' as name,
                        is_company,
                        street,
                        zip,
                        city,
                        phone,
                        fax,
                        mobile,
                        email,
                        website,
                        function,
                        is_type_partenaire,
                        is_region_id,
                        is_secteur_activite_id 
                    from res_partner 
                    where parent_id is null and active='t'
                ) rp
            );
        """)



