# -*- coding: utf-8 -*-

import json
import logging
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
            try:
                move.action_send_akyos()
            except Exception as e:
                _logger.error("Akyos erreur envoi facture %s : %s", move.name, str(e))
                move.message_post(body="Erreur envoi Akyos : %s" % str(e))
        return res

    def action_send_akyos(self):
        self.ensure_one()
        company = self.company_id

        # Récupère la commande liée à la facture
        sale_orders = self.invoice_line_ids.sale_line_ids.order_id
        if not sale_orders:
            raise UserError(_("Aucune commande de vente liée à cette facture."))
        sale_order = sale_orders[0]

        # Génère le PDF de la facture
        pdf_content, _report_type = self.env['ir.actions.report']._render_qweb_pdf(
            'account.report_invoice', self.ids
        )

        file_name = "%s.pdf" % (self.name or "facture")

        payload = company.send_document_to_akyos(
            doc_type='invoice',
            external_id=self.name,
            chantier_id=sale_order.name,
            pdf_content=pdf_content,
            file_name=file_name,
        )

        _logger.info("Akyos facture envoyée : %s -> commande %s", self.name, sale_order.name)
        body = Markup(
            "<b>Facture envoyée vers Akyos</b><br/>"
            "<pre>%s</pre>"
        ) % json.dumps(payload, indent=2, ensure_ascii=False)
        sale_order.message_post(
            body=body,
            attachments=[(file_name, pdf_content)],
        )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_account_invoice_line_id = fields.Integer('Lien entre account_invoice_line et account_move_line pour la migration')



