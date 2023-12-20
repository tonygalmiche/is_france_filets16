# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools
from odoo.exceptions import Warning
import datetime
import codecs
import unicodedata
import base64


def s(txt):
    if type(txt)!=unicode:
        txt = unicode(txt,'utf-8')
    txt = unicodedata.normalize('NFD', txt).encode('ascii', 'ignore')
    return txt


class is_export_compta(models.Model):
    _name='is.export.compta'
    _description = "is_export_compta"
    _order='name desc'

    name               = fields.Char(u"N°Folio", readonly=True)
    journal = fields.Selection([
        ('VT', 'Ventes'),
        ('HA', 'Achats'),
    ], 'Journal', default='VT',required=True)
    date_debut         = fields.Date(u"Date de début", required=True)
    date_fin           = fields.Date(u"Date de fin"  , required=True)
    ligne_ids          = fields.One2many('is.export.compta.ligne', 'export_compta_id', u'Lignes')
    _defaults = {
    }


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.export.compta')
        return super().create(vals_list)


    def generer_lignes_action(self):
        cr=self._cr
        for obj in self:
            obj.ligne_ids.unlink()
            sql="""
                SELECT  
                    aml.date,
                    aa.code, 
                    aa.name,
                    ai.number,
                    aml.account_id,
                    aml.credit-aml.debit
                FROM account_move_line aml left outer join account_invoice ai        on aml.move_id=ai.move_id
                                           inner join account_account aa             on aml.account_id=aa.id
                                           left outer join res_partner rp            on aml.partner_id=rp.id
                                           inner join account_journal aj             on aml.journal_id=aj.id
                WHERE 
                    aml.date>='"""+str(obj.date_debut)+"""' and 
                    aml.date<='"""+str(obj.date_fin)+"""' and 
                    aj.code='FAC'
                ORDER BY ai.number, aml.id
            """
            cr.execute(sql)
            ct=0
            for row in cr.fetchall():
                ct=ct+1
                montant=row[5]
                debit=0
                credit=0
                if montant<0:
                    debit=-montant
                else:
                    credit=montant

                date_facture=row[0]
                date=date_facture
                date=datetime.datetime.strptime(date, '%Y-%m-%d')
                date=date.strftime('%d/%m/%Y')

                if montant:
                    vals={
                        'export_compta_id'  : obj.id,
                        'ligne'             : ct,
                        'date_facture'      : date_facture,
                        'account_id'        : row[4],
                        'libelle'           : s(row[2][0:29]),
                        'piece'             : row[3],
                        'journal'           : obj.journal,
                        'debit'             : debit,
                        'credit'            : credit,
                        'devise'            : u'EUR',
                    }


                    self.env['is.export.compta.ligne'].create(vals)
            self.generer_fichier_action()


    def generer_fichier_action(self):
        cr=self._cr
        for obj in self:
            name='export-compta.txt'
            model='is.export.compta'
            attachments = self.env['ir.attachment'].search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
            attachments.unlink()
            dest     = '/tmp/'+name
            f = codecs.open(dest,'wb',encoding='utf-8')
            f.write('##Transfert\r\n')
            f.write('##Section\tDos\r\n')
            f.write('EUR\r\n')
            f.write('##Section\tMvt\r\n')
            for row in obj.ligne_ids:
                compte=str(row.account_id.code or '')
                debit=row.debit
                credit=row.debit
                if row.credit>0.0:
                    montant=row.credit  
                    sens='C'
                else:
                    montant=row.debit  
                    sens='D'
                montant='%0.2f' % montant
                date=row.date_facture
                date=datetime.datetime.strptime(date, '%Y-%m-%d')
                date=date.strftime('%d/%m/%Y')
                f.write('"'+obj.name+'"\t')
                f.write('"'+obj.journal+'"\t')
                f.write('"'+date+'"\t')
                f.write('"'+compte+'"\t')
                f.write('"'+row.libelle[0:34]+'"\t')
                f.write('"'+montant+'"\t')
                f.write(sens+'\t')
                f.write('B\t')
                f.write('"'+(row.libelle or '')+'"\t')
                f.write('"'+(row.piece or '')+'"\t')
                f.write('\r\n')
            f.write('##Section\tJnl\r\n')
            f.write('"VT"\t"Ventes"\t"T"\r\n')
            f.close()
            r = open(dest,'rb').read().encode('base64')
            vals = {
                'name':        name,
                'datas_fname': name,
                'type':        'binary',
                'res_model':   model,
                'res_id':      obj.id,
                'datas':       r,
            }
            id = self.env['ir.attachment'].create(vals)



class is_export_compta_ligne(models.Model):
    _name = 'is.export.compta.ligne'
    _description = "Lignes d'export en compta"
    _order='ligne,id'

    export_compta_id = fields.Many2one('is.export.compta', 'Export Compta', required=True, ondelete='cascade')
    ligne            = fields.Integer("Ligne")
    date_facture     = fields.Date("Date")
    journal          = fields.Char("Journal")
    account_id       = fields.Many2one('account.account', u"N°Compte")
    libelle          = fields.Char(u"Libellé Compte")
    piece            = fields.Char(u"Pièce")
    debit            = fields.Float(u"Débit")
    credit           = fields.Float(u"Crédit")
    devise           = fields.Char(u"Devise")
    commentaire      = fields.Char(u"Commentaire")

    _defaults = {
        'devise' : 'E',
    }



