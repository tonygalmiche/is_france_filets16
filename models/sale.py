# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from odoo.http import request
import os
import base64
from shutil import copy
import subprocess
import logging
_logger = logging.getLogger(__name__)


_ETAT_PLANNING=[
    ('a_confirmer', 'A confirmer'),
    ('a_faire'    , 'A faire'),
    ('fait'       , 'Fait'),
]


_TYPE_CHANTIER=[
    ('neuf'           , 'Neuf'),
    ('renovation'     , 'Rénovation'),
    ('neuf_renovation', 'Neuf et Rénovation'),
]


_CHOIX_PV=[
    ('C' , 'Conforme'),
    ('NC', 'non Conforme'),
]


_TYPE_COUT=[
    ('MO'  , 'MO'),
    ('Achats', 'Achats'),
]


class IsControleGestion(models.Model):
    _name='is.controle.gestion'
    _description = "IsControleGestion"
    _order='ordre,name'

    name      = fields.Char("Contrôle de gestion", required=True)
    ordre     = fields.Integer("Ordre", required=True)
    type_cout = fields.Selection(_TYPE_COUT, 'Type de coût', default='MO', required=True)


class IsSaleOrderControleGestion(models.Model):
    _name='is.sale.order.controle.gestion'
    _description = "IsSaleOrderControleGestion"
    _order='order_id,ordre,controle_gestion_id'

    order_id            = fields.Many2one('sale.order', 'Commande', required=True, ondelete='cascade', readonly=True,index=True)
    controle_gestion_id = fields.Many2one('is.controle.gestion', 'Description')
    ordre               = fields.Integer("Ordre"             , compute='_compute', readonly=True, store=True)
    type_cout           = fields.Selection(_TYPE_COUT, 'Type', compute='_compute', readonly=True, store=True)
    montant_prevu       = fields.Integer("Montant prévu")
    montant_realise     = fields.Integer("Montant réalisé")
    ecart               = fields.Integer("Ecart", compute='_compute', readonly=True, store=True)

    @api.depends('controle_gestion_id','montant_prevu','montant_realise')
    def _compute(self):
        for obj in self:
            ordre = 0
            type_cout = False
            if  obj.controle_gestion_id:
                ordre     = obj.controle_gestion_id.ordre
                type_cout = obj.controle_gestion_id.type_cout
            obj.ordre     = ordre
            obj.type_cout = type_cout
            obj.ecart     = obj.montant_prevu - obj.montant_realise


class IsMotifArchivage(models.Model):
    _name='is.motif.archivage'
    _description = "IsMotifArchivage"
    _order='name'

    name = fields.Char(u"Motif d'Archivage")


class IsTypePrestation(models.Model):
    _name='is.type.prestation'
    _description = "IsTypePrestation"
    _order='name'

    name = fields.Char(u'Type de prestation')


class IsNacelle(models.Model):
    _name='is.nacelle'
    _description = "IsNacelle"
    _order='name'

    name = fields.Char(u'Nacelle')


class IsEquipeAbsence(models.Model):
    _name='is.equipe.absence'
    _description = "IsEquipeAbsence"
    _order='date_debut'

    equipe_id  = fields.Many2one('is.equipe', 'Equipe', required=True, ondelete='cascade', readonly=True)
    date_debut = fields.Date(u'Date début', index=True)
    date_fin   = fields.Date(u'Date fin')
    motif      = fields.Char(u'Motif absence')


class IsEquipeMessage(models.Model):
    _name='is.equipe.message'
    _description = "IsEquipeMessage"
    _order='date'

    equipe_id = fields.Many2one('is.equipe', 'Equipe', required=True, ondelete='cascade', readonly=True)
    date      = fields.Date('Date', index=True)
    message   = fields.Char('Message')


class IsEquipe(models.Model):
    _name='is.equipe'
    _description = "IsEquipe"
    _order='name'

    name            = fields.Char(u'Equipe', required=True)
    user_id         = fields.Many2one('res.users', "Chef d'équipe", required=True)
    chef_secteur_id = fields.Many2one('res.users', "Chef de secteur", help="Un chef de secteur est responsable d'une ou plusieurs équipes")
    absence_ids     = fields.One2many('is.equipe.absence', 'equipe_id', u"Absences")
    message_ids     = fields.One2many('is.equipe.message', 'equipe_id', u"Messages")


    def get_absences(self):
        dates=[]
        for line in self.sudo().absence_ids:
            d1=line.date_debut
            d2=line.date_fin
            jours=(d2-d1).days+1
            for d in range(0, jours):
                if d1 not in dates:
                    dates.append(d1)
                d1=d1+timedelta(days=1)
        return dates


    def test_dispo_planning(self, date):
        """Retourne le nombre de fois ou l'équipe apparait sur le planning pour la date indiquée (si 0, alors l'équipe est dispo)"""
        cr = self._cr
        SQL="""
            select p.id,p.date_debut,p.date_fin, p.commentaire
            from is_sale_order_planning p join is_sale_order_planning_equipe_rel rel  on p.id=rel.order_id
            where 
                date_debut<=%s and 
                date_fin>=%s and
                rel.equipe_id=%s
        """
        cr.execute(SQL,[date,date,self.id])
        res = cr.fetchall()
        return len(res)


class IsDepartement(models.Model):
    _name='is.departement'
    _description = "Département"
    _order='name'

    name        = fields.Char('Département', required=True)
    equipe_ids  = fields.Many2many('is.equipe','is_departement_equipe_rel','departement_id','equipe_id', string="Equipes")


    def get_dates(self,departement=False, limite=60):
        dates=[]
        if departement:
            lines = self.env['is.departement'].search([('name','=',departement)])
            for line in lines:
                date = datetime.today().date()
                if date not in dates:
                    for equipe in line.equipe_ids:
                        absences=equipe.get_absences()
                        for x in range(0, limite):
                            jour = date.isoweekday()
                            if jour<6:
                                res=equipe.test_dispo_planning(date)
                                if res==0:
                                    if date not in absences:
                                        dates.append(date)
                            date = date + timedelta(days=1)
        return dates


    def get_equipe(self, date=False):
        if date:
            for obj in self:
                for equipe in obj.equipe_ids:
                    absences=equipe.get_absences()
                    jour = date.isoweekday()
                    if jour<6:
                        res=equipe.test_dispo_planning(date)
                        if res==0:
                            if date not in absences:
                                return equipe
        return False


class IsSaleOrderPlanning(models.Model):
    _name='is.sale.order.planning'
    _description = "IsSaleOrderPlanning"
    _order='order_id,date_debut'


    @api.depends('date_debut','date_fin','equipe_ids')
    def _compute_alerte(self):
        for obj in self:
            avertissements=False
            if obj.equipe_ids and obj.date_debut and obj.date_fin:
                d1=obj.date_debut
                d2=obj.date_fin
                jours=(d2-d1).days+1
                for d in range(0, jours):
                    for equipe in obj.equipe_ids:
                        res=self.get_avertissements(obj,equipe,d1)
                        if res:
                            if avertissements:
                                avertissements.extend(res)
                            else:
                                avertissements=res
                    d1=d1+timedelta(days=1)
            if avertissements:
                avertissements="\n".join(avertissements)
            obj.alerte = avertissements


    order_id       = fields.Many2one('sale.order', 'Commande', required=True, ondelete='cascade', readonly=True,index=True)
    date_debut     = fields.Date(u'Date début',index=True)
    date_fin       = fields.Date(u'Date fin')
    commentaire    = fields.Text('Commentaire planning')
    equipe_ids     = fields.Many2many('is.equipe','is_sale_order_planning_equipe_rel','order_id','equipe_id', string="Equipes")
    pose_depose    = fields.Selection([
        ('pose'  , 'Pose'),
        ('depose', 'Dépose'),
    ], u'Pose / Dépose')
    etat = fields.Selection(_ETAT_PLANNING, u'État', default='a_confirmer')
    realisation    = fields.Text(u'Réalisation', help=u'Réalisation du chantier', readonly=True)
    pv_realise = fields.Char('PV')

    sms_heure    = fields.Datetime(u"Heure d'envoi du SMS")
    sms_mobile   = fields.Char(u"Mobile")
    sms_message  = fields.Text(u"Message")
    sms_resultat = fields.Char(u"Résultat")
    sms_quota    = fields.Integer(u"Quota OVH")
    alerte       = fields.Text(u"Alerte", compute='_compute_alerte', readonly=True)


    def onchange_dates(self,date_debut,date_fin):
        if date_debut and date_fin:
            if date_fin < date_debut:
                warning = {
                    'title': 'Attention !',
                    'message' : u'La date de fin est inférieure à la date de début'
                }
                return {'warning': warning}


    def get_avertissements(self,obj,equipe,date):
        avertissements=[]

        date=date.strftime('%d/%m/%Y')
        #** Recherche s'il existe une absence ******************
        message=self.env['is.creation.planning'].get_absence(equipe, date)
        if message:
            avertissements.append(equipe.name+u' est absent le '+date+u' ('+message+')')
        #*******************************************************

        #** Recherche s'il existe déja une autre affaire *******
        chantiers=self.env['is.creation.planning'].get_chantiers(equipe, date, retour='order')
        if chantiers:
            for chantier in chantiers:
                if chantier!=obj.order_id.name:
                    avertissements.append(u'Le chantier '+chantier+u" est déjà plannifié pour l'équipe "+equipe.name+u' le '+date)
        #*******************************************************

        return avertissements




class SaleOrder(models.Model):
    _inherit = "sale.order"


    @api.depends('is_planning_ids')
    def _compute(self):
        for obj in self:
            etat=[]
            for line in obj.is_planning_ids:
                if line.etat and line.date_debut and line.date_fin:
                    x=dict(_ETAT_PLANNING)[line.etat]
                    etat.append(x)
            if etat:
                etat=', '.join(etat)
            else:
                etat=''
            obj.is_etat_planning=etat


    def _compute_ca_m2(self):
        for obj in self:
            ca=0
            if obj.is_superficie_m2:
                ca=obj.is_ca_hors_nacelle/obj.is_superficie_m2
            obj.is_ca_m2=ca


    @api.depends('is_controle_gestion_ids')
    def _compute_totaux(self):
        for obj in self:
            total_mo_prevu       = 0
            total_achats_prevu   = 0
            total_mo_realise     = 0
            total_achats_realise = 0
            for line in obj.is_controle_gestion_ids:
                if line.type_cout == 'MO':
                    total_mo_prevu   += line.montant_prevu
                    total_mo_realise += line.montant_realise
                if line.type_cout == 'Achats':
                    total_achats_prevu   += line.montant_prevu
                    total_achats_realise += line.montant_realise
            obj.is_total_mo_prevu       = total_mo_prevu
            obj.is_total_achats_prevu   = total_achats_prevu
            obj.is_total_mo_realise     = total_mo_realise
            obj.is_total_achats_realise = total_achats_realise
            obj.is_ecart_mo             = total_mo_prevu - total_mo_realise
            obj.is_ecart_achat          = total_achats_prevu - total_achats_realise


    @api.depends('is_nb_jours_prevu','is_nb_jours_realise')
    def _compute_nb_jours(self):
        for obj in self:
            obj.is_ecart_jours = obj.is_nb_jours_prevu - obj.is_nb_jours_realise



    @api.depends('order_line')
    def _compute_classification(self):
        for obj in self:
            ids=[]
            for line in obj.order_line:
                x = line.product_id.default_code
                if x:
                    x=x.split(' ')
                    if x[0] not in ids:
                        ids.append(x[0])
            ids.sort()
            obj.is_classification = ','.join(ids)


    #@api.depends('partner_id','partner_id.is_type_partenaire')
    def _compute_type_partenaire(self):
        for obj in self:
            obj.is_type_partenaire = obj.partner_id.is_type_partenaire


    @api.depends('order_line')
    def _compute_ca_nacelle(self):
        for obj in self:
            ca=0
            for line in obj.order_line:
                if line.product_id and line.product_id.default_code:
                    if line.product_id.default_code=='location nacelle':
                        ca+=line.price_subtotal
            obj.is_ca_nacelle = ca
            obj.is_ca_hors_nacelle = obj.amount_untaxed - ca


    @api.depends('order_line','is_suivi')
    def _compute_suivi_ht(self):
        for obj in self:
            obj.is_suivi_ht = obj.amount_untaxed*obj.is_suivi/100


    @api.depends('is_planning_ids')
    def _compute_chantier_id(self):
        for obj in self:
            chantiers = self.env['is.chantier'].search([('order_id','=',obj.id)])
            is_chantier_id = False
            is_filet_ids   = False
            for chantier in chantiers:
                is_chantier_id = chantier.id
                is_filet_ids   = chantier.filet_ids
            obj.is_chantier_id = is_chantier_id
            obj.is_filet_ids   = is_filet_ids


    is_nom_chantier         = fields.Char(u'Nom du chantier')
    is_date_previsionnelle  = fields.Date(u'Date prévisionnelle du chantier')
    is_contact_id           = fields.Many2one('res.partner', u'Contact du client')
    is_distance_chantier    = fields.Integer(u'Distance du chantier (en km)')
    is_num_ancien_devis     = fields.Char(u'N°ancien devis')
    is_ref_client           = fields.Char(u'Référence client')
    is_motif_archivage_id   = fields.Many2one('is.motif.archivage', u'Motif archivage devis')
    is_motif_archivage      = fields.Text(u'Motif archivage devis (commentaire)')
    is_entete_devis         = fields.Text(u'Entête devis')
    is_pied_devis           = fields.Text(u'Pied devis')
    is_superficie           = fields.Char(u'Superficie', help=u"Champ utilisé pour le devis client")
    is_superficie_m2        = fields.Integer(u'Superficie (m2)', help=u"Champ utilisé pour les calculs du CA/m2")
    is_ca_nacelle           = fields.Float(u"CA nacelle"     , digits=(14,2), compute='_compute_ca_nacelle', readonly=True, store=True)
    is_ca_hors_nacelle      = fields.Float(u"CA hors nacelle", digits=(14,2), compute='_compute_ca_nacelle', readonly=True, store=True)
    is_ca_m2                = fields.Float(u"CA / m2", digits=(14,2), compute='_compute_ca_m2', readonly=True)
    is_hauteur              = fields.Char(u'Hauteur')
    is_nb_interventions     = fields.Char(u"Nombre d'interventions")
    is_type_chantier        = fields.Selection(_TYPE_CHANTIER, u'Type de chantier')
    is_type_prestation_id   = fields.Many2one('is.type.prestation', u'Type de prestation')
    is_nacelle_id           = fields.Many2one('is.nacelle', u'Nacelle')
    is_planning_ids         = fields.One2many('is.sale.order.planning', 'order_id', u"Planning")

    is_chantier_id          = fields.Many2one('is.chantier', u'Chantier', compute='_compute_chantier_id', readonly=True, store=False)
    is_filet_ids            = fields.One2many('is.filet', 'chantier_id', u"Filets", compute='_compute_chantier_id', readonly=True, store=False)

    is_etat_planning        = fields.Char(u"Etat planning", compute='_compute', readonly=True, store=True)
    is_info_fiche_travail   = fields.Text(u'Informations fiche de travail')
    is_piece_jointe_ids     = fields.Many2many('ir.attachment', 'sale_order_piece_jointe_attachment_rel', 'order_id', 'attachment_id', u'Pièces jointes')
    is_region_id            = fields.Many2one('is.region'          , u'Région'            , related='partner_id.is_region_id'          , readonly=True)
    is_secteur_activite_id  = fields.Many2one('is.secteur.activite', u"Secteur d'activité", related='partner_id.is_secteur_activite_id', readonly=True)
    is_controle_gestion_ids = fields.One2many('is.sale.order.controle.gestion', 'order_id', u"Contrôle de gestion")

    is_nb_jours_prevu       = fields.Integer(u'Nb jours prévu')
    is_nb_jours_realise     = fields.Integer(u'Nb jours réalisé')
    is_ecart_jours          = fields.Integer(u'Écart jours'         , compute='_compute_nb_jours', readonly=True, store=True)
    is_total_mo_prevu       = fields.Integer(u'Total MO prévu'      , compute='_compute_totaux'  , readonly=True, store=True)
    is_total_achats_prevu   = fields.Integer(u'Total Achats prévu'  , compute='_compute_totaux'  , readonly=True, store=True)
    is_total_mo_realise     = fields.Integer(u'Total MO réalisé'    , compute='_compute_totaux'  , readonly=True, store=True)
    is_total_achats_realise = fields.Integer(u'Total Achats réalisé', compute='_compute_totaux'  , readonly=True, store=True)
    is_ecart_mo             = fields.Integer(u'Écart MO'            , compute='_compute_totaux'  , readonly=True, store=True)
    is_ecart_achat          = fields.Integer(u'Écart Achat'         , compute='_compute_totaux'  , readonly=True, store=True)

    is_classification       = fields.Char(u'Classification'         , compute='_compute_classification', readonly=True, store=True)

    is_type_partenaire = fields.Selection([
        ('Client'      , 'Client'),
        ('Prospect'    , 'Prospect'),
        ('Prescripteur', 'Prescripteur'),
    ], u'Type de partenaire' , compute='_compute_type_partenaire', readonly=True, store=True)

    is_suivi    = fields.Integer(u'Suivi(%)' , help=u'Utilisé dans la gestion des offres')
    is_suivi_ht = fields.Integer(u'Suivi (€)', help=u'Utilisé dans la gestion des offres', compute='_compute_suivi_ht', readonly=True, store=True)
    is_montant_regle_en_ligne = fields.Float('Montant réglé en ligne (€)', digits=(14,2))
    is_utilisateur_reserve    = fields.Char("Utilisateur ayant réservé le chantier")


    def get_nacelles(self):
        nacelles = self.env['is.nacelle'].search([])
        return nacelles


    def init_controle_gestion_action(self):
        for obj in self:
            if not obj.is_controle_gestion_ids:
                lines = self.env['is.controle.gestion'].search([])
                for line in lines:
                    vals={
                        'order_id'           : obj.id,
                        'controle_gestion_id': line.id
                    }
                    res = self.env['is.sale.order.controle.gestion'].create(vals)


    def forcer_entierement_facture_action(self):
        for obj in self:
            obj.invoice_status = 'invoiced'


    def create_akyos_order(self, code_client=False, departement=False, zone=False, tarif_ht=False, montant_paye=False, date_reservee=False, prestation=False,nom_chantier=False, utilisateur=False):
        res={}
        err=False
        prestations={
            1: "PRESTATION-01",
            2: "PRESTATION-02",
        }
        prestation = int(prestation)
        err=False
        if prestation not in prestations:
            err="prestation inconnue ou non définie"
        if not err:
            code = prestations[prestation]
            products = self.env['product.template'].search([('default_code','=',code)], limit=1)
            if len(products):
                product=products[0]
            else:
                err="prestation %s (%s) non trouvée dans Odoo"%(prestation,code)
        if not err:
            partners = self.env['res.partner'].search([('is_code_client_ebp','=',code_client)], limit=1)
            if len(partners)==0:
                err="Code client %s non trouvée dans Odoo"%(code_client)
            else:
                partner=partners[0]
        if not err:
            departements = self.env['is.departement'].search([('name','=',departement)], limit=1)
            if len(departements)==0:
                err="Département (%s) non trouvée dans Odoo"%(departement)
            else:
                departement=departements[0]
                date=datetime.strptime(date_reservee, '%Y-%m-%d').date()
                equipe=departement.get_equipe(date)
                if not equipe:
                    err="Aucune équipe disponible pour le %s"%(date)
        if not err:
            vals={
                'partner_id'               : partner.id,
                'is_nom_chantier'          : nom_chantier,
                'is_montant_regle_en_ligne': montant_paye,
                'is_utilisateur_reserve'   : utilisateur,
            }
            order = self.env['sale.order'].create(vals)
            if order:
                numcde = order.name
                res["numcde"]=numcde
                vals={
                    'order_id'       : order.id,
                    'product_id'     : product.id,
                    'name'           : product.name,
                    'product_uom_qty': 1,
                    'price_unit'     : tarif_ht,
                }
                line = self.env['sale.order.line'].create(vals)
        if not err:
            vals={
                'order_id'   : order.id,
                'date_debut' : date_reservee,
                'date_fin'   : date_reservee,
                'equipe_ids' : [(6,0,[equipe.id])],
                'pose_depose': 'pose',
            }
            line = self.env['is.sale.order.planning'].sudo().create(vals)
        res["err"]=err
        return(res)


    def create_akyos_depose(self, numcde=False, departement=False, date_reservee=False):
        res={}
        err=False
        orders = self.env['sale.order'].search([('name','=',numcde)], limit=1)
        if len(orders)==0:
            err="Commande client %s non trouvée dans Odoo"%(numcde)
        else:
            order=orders[0]
        if not err:
            departements = self.env['is.departement'].search([('name','=',departement)], limit=1)
            if len(departements)==0:
                err="Département (%s) non trouvée dans Odoo"%(departement)
            else:
                departement=departements[0]
                date=datetime.strptime(date_reservee, '%Y-%m-%d').date()
                equipe=departement.get_equipe(date)
                if not equipe:
                    err="Aucune équipe disponible pour le %s"%(date)
        if not err:
            vals={
                'order_id'   : order.id,
                'date_debut' : date_reservee,
                'date_fin'   : date_reservee,
                'equipe_ids' : [(6,0,[equipe.id])],
                'pose_depose': 'depose',
            }
            line = self.env['is.sale.order.planning'].sudo().create(vals)
        res["err"]=err
        return(res)


class IsCreationPlanningPreparation(models.Model):
    _name='is.creation.planning.preparation'
    _description = "IsCreationPlanningPreparation"
    _order='date,equipe_id,order_id'

    planning_id  = fields.Many2one('is.creation.planning', u'Planning', required=True, ondelete='cascade')
    date         = fields.Date(u'Date', index=True)
    equipe_id    = fields.Many2one('is.equipe', u'Equipe')
    order_id     = fields.Many2one('sale.order', u'Chantier')
    nom_chantier = fields.Char(u'Nom du chantier')
    partner_id   = fields.Many2one('res.partner', u'Client')
    pose_depose  = fields.Selection([
        ('pose'  , 'Pose'),
        ('depose', 'Dépose'),
    ], u'Pose / Dépose')
    etat    = fields.Selection(_ETAT_PLANNING, u'État')
    message = fields.Text('Message')


class IsCreationPlanning(models.Model):
    _name='is.creation.planning'
    _description = "IsCreationPlanning"
    _order='date_debut desc'

    date_debut   = fields.Date(u'Date de début', required=True)
    date_fin     = fields.Date(u'Date de fin'  , required=True)
    equipe_id    = fields.Many2one('is.equipe', u'Equipe')
    planning_ids = fields.One2many('is.creation.planning.preparation', 'planning_id', u"Planning")


    def name_get(self):
        res=[]
        for obj in self:
            res.append((obj.id, obj.date_debut))
        return res


    def get_dates(self):
        cr = self._cr
        dates=[]
        for obj in self:
            d1=obj.date_debut
            d2=obj.date_fin
            jours=(d2-d1).days+1
            for d in range(0, jours):
                dates.append(d1.strftime('%d/%m/%Y'))
                d1=d1+timedelta(days=1)
        return dates


    def get_equipes(self):
        equipes = self.env['is.equipe'].search([])
        return equipes


    def get_absence(self,equipe,date):
        """Recherche des absences pour cette équipe et cette date"""
        cr = self._cr
        d=datetime.strptime(date, '%d/%m/%Y')
        absence=False
        if isinstance(equipe.id, int):
            equipe_id = equipe.id
        else:
            equipe_id = equipe._origin.id
        SQL="""
            SELECT iea.motif 
            FROM is_equipe_absence iea
            WHERE 
                iea.date_debut<='"""+str(d)+"""' and 
                iea.date_fin>='"""+str(d)+"""' and
                iea.equipe_id="""+str(equipe_id)+"""
        """
        cr.execute(SQL)
        res = cr.fetchall()
        for row in res:
            absence=row[0]
        return absence


    def get_message(self,equipe,date):
        """Recherche des messages pour cette équipe et cette date"""
        cr = self._cr
        d=datetime.strptime(date, '%d/%m/%Y')
        message=[]
        for obj in self:
            SQL="""
                SELECT iem.message 
                FROM is_equipe_message iem
                WHERE 
                    iem.date='"""+str(d)+"""' and 
                    iem.equipe_id="""+str(equipe.id)+"""
            """
            cr.execute(SQL)
            res = cr.fetchall()
            

            for row in res:
                message.append(row[0])
        return '<br />'.join(message)


    def get_orders(self,date_debut,date_fin):
        """Retourne les commandes pour les fiches de travail"""
        cr = self._cr
        SQL="""
            SELECT DISTINCT so.id, so.name
            FROM is_sale_order_planning isop inner join sale_order so on isop.order_id=so.id
            WHERE 
                isop.date_debut<='"""+str(date_fin)+"""' and 
                isop.date_fin>='"""+str(date_debut)+"""'
            ORDER BY so.name
        """
        cr.execute(SQL)
        res = cr.fetchall()
        orders=[]
        for row in res:
            if row[0]:
                order = self.env['sale.order'].browse(row[0])
                if order:
                    if order not in orders:
                        orders.append(order)
        return orders


    def get_chantiers(self,equipe,date,retour='html'):
        cr = self._cr
        d=datetime.strptime(date, '%d/%m/%Y')
        chantiers=[]

        if isinstance(equipe.id, int):
            equipe_id = equipe.id
        else:
            equipe_id = equipe._origin.id

        SQL="""
            SELECT
                so.name,
                rp.name,
                so.is_nom_chantier,
                so.is_type_chantier,
                so.is_superficie,
                isop.commentaire,
                isop.pose_depose,
                isop.etat,
                so.id,
                isop.id
            FROM is_sale_order_planning isop inner join sale_order so on isop.order_id=so.id 
                                             inner join is_sale_order_planning_equipe_rel rel on isop.id=rel.order_id
                                             inner join is_equipe ie on rel.equipe_id=ie.id
                                             inner join res_partner rp on so.partner_id=rp.id
            WHERE 
                isop.date_debut<='"""+str(d)+"""' and 
                isop.date_fin>='"""+str(d)+"""' and
                ie.id="""+str(equipe_id)+"""
        """
        cr.execute(SQL)
        res = cr.fetchall()
        for row in res:
            if retour=='html':
                pose_depose=row[6]
                if pose_depose=='pose':
                    pose_depose='<span style="color:Red">Pose</span>'
                if pose_depose=='depose':
                    pose_depose=u'<span style="color:LawnGreen">Dépose</span>'
                html='<div>'
                etat=row[7]
                color='red'
                if etat=='a_confirmer':
                    color='red'
                if etat=='a_faire':
                    color='SteelBlue'
                if etat=='fait':
                    color='LawnGreen'
                html+='<b><span style="background-color:'+color+'">'+(row[0] or '')+'</span></b>'
                if pose_depose:
                    html+=' - <b>'+pose_depose+'</b>'
                html+='</div>'
                html+='<b>'+(row[1] or '')+'</b><br />'
                html+=(row[2] or '')+'<br />'
                html+=(row[3] or '')+' - '+(row[4] or '')+'<br />'
                html+=(row[5] or '')
                chantiers.append(html)
            if retour=='order':
                chantiers.append(row[0])
            if retour=='planning':
                vals={
                    'order_id'   : row[8],
                    'planning_id': row[9],
                }
                chantiers.append(vals)
        return chantiers


    def mail_planning_action(self):
        """Mail du planning"""
        mails=[]
        for obj in self:
            for planning in obj.planning_ids:
                mail=planning.equipe_id.user_id.partner_id.email
                if mail and mail not in mails:
                    mails.append(mail)
            email_to=','.join(mails)
            subject=u'Planning du '+str(obj.date_debut)+u' au '+str(obj.date_fin)
            user  = self.env['res.users'].browse(self._uid)
            email_from = user.email
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url=base_url+u'/web'
            body_html=u"""
                <p>Bonjour,</p>
                <p>Le nouveau <a href='"""+url+u"""'>Planning</a> est disponible.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            vals={
                'email_from'    : email_from, 
                'email_to'      : email_to, 
                'email_cc'      : email_from,
                'subject'       : subject,
                'body_html'     : body_html, 
            }
            email=self.env['mail.mail'].create(vals)
            if email:
                self.env['mail.mail'].send(email)


    def _format_mobile(self,mobile):
        err=''
        if not mobile:
            err=u'Mobile non renseigné pour le contact'
        else:
            mobile = mobile.replace(' ','')
            if len(mobile)!=10:
                err=u'Le numéro doit contenir 10 chiffres'
            else:
                if mobile[0:2]!='06' and mobile[0:2]!='07':
                    err=u'Le numéro du mobile doit commencer par 06 ou 07'
                else:
                    mobile='0033'+mobile[-9:]
        return mobile,err


        return mobile


    def sms_planning_action(self):
        """SMS du planning"""
        cr,uid,context,su = self.env.args
        #Offset à prendre pour tenir compte des jours ouvrés
        offsets={
            0: 3, #Lundi
            1: 3, #Mardi
            2: 5, #Mercredi
            3: 5, #Jeudi
            4: 5, #Vendredi
            5: 5, #Samedi
            6: 4, #Dimanche
        }
        for obj in self:
            date_debut = datetime.today()
            jour = date_debut.weekday()
            offset = offsets[jour]
            date_fin = date_debut + timedelta(days=offset)
            lines = self.env['is.sale.order.planning'].search([
                ('date_debut','>=',date_debut),
                ('date_debut','<=',date_fin),
                ('pose_depose','=','pose'),
                ('sms_heure','=',False),
            ])
            for line in lines:
                order = line.order_id
                mobile = order.is_contact_id.mobile or order.is_contact_id.phone
                mobile,err = self._format_mobile(mobile)
                message=''
                quota=0
                if err=='':
                    err='ok'
                    user = self.env['res.users'].browse(uid)
                    company = user.company_id
                    message = company.is_sms_message or ''
                    message = message.replace('[date_debut]',date_fin.strftime('%d/%m/%Y'))
                    message = message.replace('\n',' ')
                    #message = unicode(message,'utf-8')
                    #message = unicodedata.normalize('NFD', message).encode('ascii', 'ignore')
                    if company.is_sms_mobile:
                        to,err2 = self._format_mobile(company.is_sms_mobile)
                    else:
                        to = mobile
                    param = \
                        'account='+(company.is_sms_account or '')+\
                        '&login='+(company.is_sms_login or '')+\
                        '&password='+(company.is_sms_password or '')+\
                        '&from='+(company.is_sms_from or '')+\
                        '&to='+to+\
                        '&message='+message
                    cde = 'curl --data "'+param+'" https://www.ovh.com/cgi-bin/sms/http2sms.cgi'
                    res=os.popen(cde).readlines()
                    if len(res)>=2:
                        if res[0].strip()=='OK':
                            err='OK'
                            quota = int(float(res[1].strip()))
                    else:
                        err='\n'.join(res)
                    ct=0
                    for l in res:
                        ct+=1
                line.write({
                    'sms_heure' : date_debut,
                    'sms_message': message,
                    'sms_resultat': err,
                    'sms_mobile'  : mobile or '?',
                    'sms_quota'   : quota,
                })
            return {
                'name': u'SMS',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.sale.order.planning',
                'domain': [
                    ('sms_mobile','!=', ''),
                ],
                'type': 'ir.actions.act_window',
            }


    def preparer_planning_action(self):
        """Préparation du planning"""
        for obj in self:
            obj.planning_ids.unlink()
            equipes = obj.get_equipes()
            dates   = obj.get_dates()

            orders=[]

            for equipe in equipes:
                for date in dates:
                    chantiers   = obj.get_chantiers(equipe,date,retour='planning')
                    for chantier in chantiers:
                        order_id    = chantier['order_id']
                        planning_id = chantier['planning_id']
                        order    = self.env['sale.order'].browse(order_id)
                        planning = self.env['is.sale.order.planning'].browse(planning_id)
                        d=datetime.strptime(date, '%d/%m/%Y')
                        message=self.env['is.sale.order.planning'].get_avertissements(planning,equipe,d)
                        if order not in orders:
                            orders.append(order)
                        if message:
                            message='\n'.join(message)
                        else:
                            message=False
                        if order:
                            vals={
                                'planning_id' : obj.id,
                                'date'        : d,
                                'order_id'    : order_id,
                                'equipe_id'   : equipe.id,
                                'nom_chantier': order.is_nom_chantier,
                                'partner_id'  : order.partner_id.id,
                                'pose_depose' : planning.pose_depose,
                                'etat'        : planning.etat,
                                'message'     : message,
                            }
                            self.env['is.creation.planning.preparation'].create(vals)

            #** Création des plannings pour chaque équipe **********************
            equipes = obj.get_equipes()
            for equipe in equipes:
                plannings = self.env['is.planning'].search([('creation_planning_id','=',obj.id),('equipe_id','=',equipe.id)])
                name=u'Planning du '+str(obj.date_debut)+' au '+str(obj.date_fin)+u' pour '+equipe.name
                if not plannings:
                    vals={
                        'name'                : name,
                        'equipe_id'           : equipe.id,
                        'creation_planning_id': obj.id,
                    }
                    planning=self.env['is.planning'].create(vals)
                else:
                    planning=plannings[0]
                vals={
                        'name'                : name,
                }
                planning.write(vals)
            #*******************************************************************


            #** Création des chantiers *****************************************
            self.env['is.chantier.planning'].search([('sale_order_planning_id','=',False)]).unlink()
            for order in orders:
                chantiers = self.env['is.chantier'].search([('order_id','=',order.id)])
                if not chantiers:
                    vals={
                        'order_id'         : order.id,
                    }
                    chantier=self.env['is.chantier'].create(vals)
                else:
                    chantier=chantiers[0]
                vals={
                    'name'               : order.name,
                    'client'             : order.partner_id.name,
                    'contact_client'     : order.is_contact_id.name,
                    'nom_chantier'       : order.is_nom_chantier,
                    'superficie'         : order.is_superficie,
                    'hauteur'            : order.is_hauteur,
                    'type_chantier'      : order.is_type_chantier,
                    'informations'       : order.is_info_fiche_travail,
                }
                chantier.write(vals)
                #user_ids=[]
                for line in order.is_planning_ids:
                    plannings = self.env['is.chantier.planning'].search([('sale_order_planning_id','=',line.id)])
                    if not plannings:
                        vals={
                            'chantier_id'           : chantier.id,
                            'sale_order_planning_id': line.id,
                        }
                        planning=self.env['is.chantier.planning'].create(vals)
                    else:
                        planning=plannings[0]

                    vals={
                        'date_debut'            : line.date_debut,
                        'date_fin'              : line.date_fin,
                        'commentaire'           : line.commentaire,
                        'pose_depose'           : line.pose_depose,
                        'etat'                  : line.etat,
                    }
                    planning.write(vals)
            #*******************************************************************

            #** Ajout des chantiers sur le planning ****************************
            plannings = self.env['is.planning'].search([('creation_planning_id','=',obj.id)])
            for planning in plannings:
                planning.chantier_ids.unlink()
                for order in orders:
                    test=False
                    for line in obj.planning_ids:
                        if planning.equipe_id==line.equipe_id and line.order_id==order:
                            test=True
                    if test:
                        chantiers = self.env['is.chantier'].search([('order_id','=',order.id)])
                        if chantiers:
                            chantier=chantiers[0]
                            vals={
                                'planning_id': planning.id,
                                'chantier_id': chantier.id,
                            }
                            self.env['is.planning.line'].create(vals)
            #*******************************************************************

            #** Suppression des plannings sans chantier ************************
            plannings = self.env['is.planning'].search([('creation_planning_id','=',obj.id)])
            for planning in plannings:
                unlink=True
                o=planning.creation_planning_id
                e=planning.equipe_id
                if o and e:
                    dates=o.get_dates()
                    for d in dates:
                        msg=o.get_message(e,d)
                        if msg:
                            unlink=False
                if not planning.chantier_ids and unlink:
                    planning.unlink()
            #*******************************************************************

            #** Ajout des planning PDF en pièce jointe *************************
            plannings = self.env['is.planning'].search([('creation_planning_id','=',obj.id)])
            equipe_id=obj.equipe_id.id
            for planning in plannings:
                obj.equipe_id=planning.equipe_id.id
                pdf = request.env.ref('is_france_filets16.is_planning_reports').sudo()._render_qweb_pdf([obj.id])[0]
                model=planning._name
                name='planning.pdf'
                attachment_obj = self.env['ir.attachment']
                attachments = attachment_obj.search([('res_model','=',model),('res_id','=',planning.id),('name','=',name)])
                vals = {
                    'name':        name,
                    'type':        'binary',
                    'res_model':   model,
                    'res_id':      planning.id,
                    'datas':       base64.b64encode(pdf),
                }
                if attachments:
                    for attachment in attachments:
                        attachment.write(vals)
                else:
                    attachment = attachment_obj.create(vals)
            obj.equipe_id=equipe_id
            #*******************************************************************

            return {
                'name': u'Préparation planning '+str(obj.date_debut),
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.creation.planning.preparation',
                'domain': [
                    ('planning_id','=',obj.id),
                ],
                'context':{
                    'default_planning_id': obj.id,
                },
                'type': 'ir.actions.act_window',
            }


class IsPlanningPDF(models.Model):
    _name='is.planning.pdf'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "IsPlanningPDF"
    _order='name desc'

    name    = fields.Char(u'Planning', required=True)
    user_id = fields.Many2one('res.users', u"Créateur", required=True)


class IsPlanningLine(models.Model):
    _name='is.planning.line'
    _description = "IsPlanningLine"
    _order='chantier_id'

    planning_id = fields.Many2one('is.planning', u'Planning', required=True, ondelete='cascade', readonly=True)
    chantier_id = fields.Many2one('is.chantier', u"Chantier")


class IsPlanning(models.Model):
    _name='is.planning'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "IsPlanning"
    _order='name desc'

    name                 = fields.Char(u'Planning', required=True,index=True)
    creation_planning_id = fields.Many2one('is.creation.planning', u"Préparation Planning", required=True, index=True)
    equipe_id            = fields.Many2one('is.equipe', u"Equipe")
    chef_secteur_id      = fields.Many2one(related="equipe_id.chef_secteur_id")
    chantier_ids         = fields.One2many('is.planning.line', 'planning_id', u"Chantiers")


    def generer_planning_pdf_action(self):
        cr,uid,context,su = self.env.args
        db = self._cr.dbname
        path="/tmp/planning-"+str(uid)
        cde="rm -Rf " + path
        os.popen(cde).readlines()
        if not os.path.exists(path):
            os.makedirs(path)
        paths=[]
        for obj in self:
            # ** Ajout des plannings ******************************************
            filestore = os.environ.get('HOME')+"/.local/share/Odoo/filestore/"+db+"/"
            data_dir = tools.config['data_dir']
            if data_dir:
                filestore=data_dir+"/filestore/"+db+"/"
            filtre=[
                ('name','=','planning.pdf'),
                ('res_model','=','is.planning'),
                ('res_id','=',obj.id),
            
            ]
            attachments = self.env['ir.attachment'].search(filtre,limit=1)
            for attachment in attachments:
                src = filestore+attachment.store_fname
                dst = path+"/"+str(attachment.id)+".pdf"
                if os.path.exists(src):
                    copy(src, dst)
                    paths.append(dst)
            # *****************************************************************

        # ** Merge des PDF *************************************************
        path_merged = path+"/pdf_merged.pdf"
        cmd="export _JAVA_OPTIONS='-Xms16m -Xmx64m' && pdftk "+" ".join(paths)+" cat output "+path_merged+" 2>&1"
        _logger.info(cmd)
        stream = os.popen(cmd)
        res = stream.read()
        _logger.info("res pdftk = %s",res)
        if not os.path.exists(path_merged):
            raise UserError("PDF non généré\ncmd=%s"%(cmd))
        pdfs = open(path_merged,'rb').read()
        pdfs = base64.b64encode(pdfs)
        # ******************************************************************


        # ** Creation ou modification du planning PDF **********************
        planning_pdf_obj = self.env['is.planning.pdf']
        name = 'plannings.pdf'
        plannings_pdf = planning_pdf_obj.search([('name','=',name),('user_id','=',uid)],limit=1)
        vals = {
            'name':    name,
            'user_id': uid,
        }
        if plannings_pdf:
            for planning_pdf in plannings_pdf:
                planning_pdf_id=planning_pdf.id
        else:
            planning_pdf=planning_pdf_obj.create(vals)
            planning_pdf_id=planning_pdf.id
        #**********************************************************************


        # ** Recherche si une pièce jointe est déja associèe ******************
        attachment_obj = self.env['ir.attachment']
        filtre=[
            ('name','=',name),
            ('res_model','=','is.planning.pdf'),
            ('res_id','=',planning_pdf_id),
        ]
        attachments = attachment_obj.search(filtre,limit=1)
        # ******************************************************************


        # ** Creation ou modification de la pièce jointe *******************
        vals = {
            'name'       : name,
            'type'       : 'binary',
            'datas'      : pdfs,
            'res_model'  : 'is.planning.pdf',
            'res_id'     : planning_pdf_id,
        }
        if attachments:
            for attachment in attachments:
                attachment.write(vals)
                attachment_id=attachment.id
        else:
            attachment = attachment_obj.create(vals)
            attachment_id=attachment.id
        #******************************************************************


class IsChantierPlanning(models.Model):
    _name='is.chantier.planning'
    _description = "IsChantierPlanning"
    _order='chantier_id,date_debut'

    chantier_id            = fields.Many2one('is.chantier', u'Chantier', required=True, ondelete='cascade', readonly=True,index=True)
    sale_order_planning_id = fields.Many2one('is.sale.order.planning', u"Ligne planning commande", readonly=True,index=True)
    date_debut             = fields.Date(u'Date début', readonly=True,index=True)
    date_fin               = fields.Date(u'Date fin', readonly=True)
    commentaire            = fields.Text(u'Commentaire planning', readonly=True)
    equipe_ids             = fields.Many2many('is.equipe','is_chantier_planning_equipe_rel','chantier_id','equipe_id', string=u"Equipes", readonly=True)
    pose_depose            = fields.Selection([
        ('pose'  , 'Pose'),
        ('depose', 'Dépose'),
    ], u'Pose / Dépose', readonly=True)
    etat = fields.Selection(_ETAT_PLANNING, u'État', default='a_confirmer', readonly=True)
    realisation    = fields.Text(u'Réalisation', help=u'Réalisation du chantier')
    zone_concernee = fields.Text(u'Zone concernée')

    etat_mailles = fields.Selection(_CHOIX_PV, u'Etat des mailles des filets')
    etat_mailles_obs = fields.Text('Observation état')

    reprise_mailles = fields.Selection(_CHOIX_PV, u'Reprise des mailles par couturage')
    reprise_mailles_obs = fields.Text('Observation reprise')

    point_encrage = fields.Selection(_CHOIX_PV, u"Point d'ancrage des filets")
    point_encrage_obs = fields.Text("Observation point d'ancrage")

    jointement = fields.Selection(_CHOIX_PV, u"Jointement des filets (entre eux et par rapport aux rives)")
    jointement_obs = fields.Text('Observation jointement')

    tension_filets = fields.Selection(_CHOIX_PV, u"Tension des filets")
    tension_filets_obs = fields.Text(u'Observation')

    observation = fields.Text(u'Autres observations')

    pv_realise = fields.Char(u"PV réalisé", compute='_compute', readonly=True, store=True)


    @api.depends('etat_mailles','reprise_mailles','point_encrage','jointement','tension_filets')
    def _compute(self):
        for obj in self:
            pv_realise=''
            if obj.etat_mailles and obj.reprise_mailles and obj.point_encrage and obj.jointement and obj.tension_filets:
                pv_realise='OK'
            obj.pv_realise=pv_realise


    def write(self,vals):
        res = super(IsChantierPlanning, self).write(vals)
        for obj in self:
            obj.sudo().sale_order_planning_id.pv_realise=obj.pv_realise
            if 'realisation' in vals:
                obj.sudo().sale_order_planning_id.realisation=vals['realisation']
        return res


    def saisie_pv_action(self):
        for obj in self:
            return {
                'name': "Saisie PV du chantier "+str(obj.chantier_id.name),
                'view_mode': 'form,tree',
                'view_type': 'form',
                'res_model': 'is.chantier.planning',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
            }


    def actualiser_filets_action(self):
        cr = self._cr
        for obj in self:
            if obj.chantier_id.id:
                SQL="""
                    SELECT dimensions,count(*)
                    FROM is_filet
                    WHERE chantier_id="""+str(obj.chantier_id.id)+"""
                    GROUP BY dimensions
                    ORDER BY dimensions
                """
                cr.execute(SQL)
                res = cr.fetchall()
                filets=[]
                for row in res:
                    filets.append(str(row[1])+" x "+str(row[0]))
                obj.realisation='\n'.join(filets)



class IsChantierDocument(models.Model):
    _name='is.chantier.document'
    _description = "Documents de fin de chantier"
    _order='chantier_id,id'

    chantier_id      = fields.Many2one('is.chantier', 'Chantier', required=True, ondelete='cascade', readonly=True,index=True)
    commentaire      = fields.Char('Commentaire')
    piece_jointe_ids = fields.Many2many('ir.attachment', 'is_chantier_document_attachment_rel', 'document_id', 'attachment_id', 'Pièces jointes')


class IsChantier(models.Model):
    _name='is.chantier'
    _description = "IsChantier"
    _order='name'

    name              = fields.Char('Chantier / Commande', readonly=True)
    equipe_ids        = fields.Many2many('is.equipe', string="Équipes"        , compute="_compute_equipe_ids", store=True, readonly=True)
    user_ids          = fields.Many2many('res.users', 'is_chantier_user_rel','chantier_id','user_id', string="Chefs d'équipes", compute="_compute_equipe_ids", store=True, readonly=True)
    chef_secteur_ids  = fields.Many2many('res.users', string="Chef de secteur", compute="_compute_equipe_ids", store=True, readonly=True)
    order_id          = fields.Many2one('sale.order', "Commande", readonly=True)
    client            = fields.Char('Client', readonly=True)
    contact_client    = fields.Char('Contact Client', readonly=True)
    nom_chantier      = fields.Char('Nom du chantier', readonly=True)
    superficie        = fields.Char('Superficie', readonly=True)
    hauteur           = fields.Char('Hauteur', readonly=True)
    type_chantier     = fields.Selection(_TYPE_CHANTIER, u'Type de chantier', readonly=True)
    planning_ids      = fields.One2many('is.chantier.planning', 'chantier_id', u"Planning")
    filet_ids        = fields.One2many('is.filet', 'chantier_id', u"Filets")
    informations      = fields.Text(u'Informations diverses', readonly=True)
    piece_jointe_ids  = fields.Many2many('ir.attachment', 'is_chantier_piece_jointe_attachment_rel', 'is_chantier_id', 'attachment_id', u'Pièces jointes', readonly=True)

    piece_jointe_commande_ids     = fields.Many2many('ir.attachment', u'Pièces jointes commande', compute="_compute_piece_jointe_commande_ids")

    piece_jointe_chantier_ids     = fields.Many2many('ir.attachment', 'is_chantier_piece_jointe_chantier_attachment_rel', 'is_chantier_id', 'attachment_id', u'Pièces jointes chantier')
    piece_jointe_chantier_ids_readonly = fields.Boolean('Pièces jointes commande vsb', compute="_compute_piece_jointe_chantier_ids_readonly")

    fin_chantier_ids  = fields.Many2many('ir.attachment', 'is_chantier_fin_chantier_attachment_rel', 'is_chantier_id', 'attachment_id', 'Autres documents de fin de chantier')
    fin_chantier_document = fields.One2many('is.chantier.document', 'chantier_id', "Documents de fin de chantier")


    @api.depends('order_id','order_id.write_date','order_id.is_planning_ids')
    def _compute_equipe_ids(self):
        for obj in self:
            equipe_ids=[]
            user_ids=[]
            chef_secteur_ids=[]
            for line in obj.sudo().order_id.is_planning_ids:
                for l in line.equipe_ids:
                    if l.id not in equipe_ids:
                        equipe_ids.append(l.id)
                    if l.chef_secteur_id.id not in chef_secteur_ids:
                        chef_secteur_ids.append(l.chef_secteur_id.id)
                    if l.user_id.id not in user_ids:
                        user_ids.append(l.user_id.id)
            obj.equipe_ids       = equipe_ids
            obj.user_ids         = user_ids
            obj.chef_secteur_ids = chef_secteur_ids


    @api.depends('piece_jointe_chantier_ids')
    def _compute_piece_jointe_chantier_ids_readonly(self):
        for obj in self:
            readonly=True
            chef_secteur_ids=[]
            for user in obj.chef_secteur_ids:
                chef_secteur_ids.append(user._origin.id)
            if self.env.user.id in chef_secteur_ids:
                readonly=False
            obj.piece_jointe_chantier_ids_readonly = readonly


    @api.depends('order_id')
    def _compute_piece_jointe_commande_ids(self):
        for obj in self:
            ids=[]
            for attachment in obj.sudo().order_id.is_piece_jointe_ids:
                #TODO : Je dois changer le res_id et le res_model de la piece jointe pour que l'utilisateur puisse y accèder
                attachment.sudo().res_id=obj.id
                attachment.sudo().res_model=obj._name
                ids.append(attachment.id)
            obj.piece_jointe_commande_ids = [(6,0,ids)]
