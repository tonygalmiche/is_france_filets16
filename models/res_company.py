# -*- coding: utf-8 -*-
import json
import requests
import requests.packages.urllib3
import logging
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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
    is_akyos_url    = fields.Char('URL webservice Akyos')
    is_akyos_key    = fields.Char('Key webservice Akyos')

    def send_document_to_akyos(self, doc_type, external_id, chantier_id, pdf_content, file_name):
        """Envoie un document PDF vers le webservice Akyos.

        :param doc_type:    'invoice' ou 'pv'
        :param external_id: identifiant externe du document (nom facture ou nom chantier)
        :param chantier_id: nom du chantier côté Akyos (sale.order.name)
        :param pdf_content: contenu binaire du PDF
        :param file_name:   nom du fichier PDF
        :raises UserError: si la configuration est manquante ou si le serveur répond avec une erreur
        """
        if not self.is_akyos_url or not self.is_akyos_key:
            raise UserError("L'URL et la clé du webservice Akyos ne sont pas configurées dans la société.")

        payload = {
            "event": "document.created",
            "document": {
                "type": doc_type,
                "external_id": external_id,
                "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "chantier_id": chantier_id,
                "file_name": file_name,
                "mime_type": "application/pdf",
            }
        }

        files = {
            'payload': (None, json.dumps(payload), 'application/json'),
            'file': (file_name, pdf_content, 'application/pdf'),
        }
        headers = {
            'X-Webhook-Key': self.is_akyos_key,
        }

        _logger.info("Akyos [%s] envoi %s : %s", doc_type, self.is_akyos_url, json.dumps(payload, ensure_ascii=False))
        try:
            requests.packages.urllib3.disable_warnings()
            response = requests.post(self.is_akyos_url, headers=headers, files=files, timeout=30, verify=False)
        except requests.exceptions.RequestException as e:
            _logger.error("Akyos connexion error (%s) : %s", self.is_akyos_url, str(e))
            raise UserError("Erreur de connexion vers Akyos (%s) : %s" % (self.is_akyos_url, str(e)))

        _AKYOS_ERRORS = {
            400: "Requête invalide (payload absent/invalide ou fichier manquant).",
            401: "Authentification webhook invalide. Vérifiez la clé Akyos.",
            404: "Chantier introuvable sur Akyos (chantier_id=%s inconnu)." % chantier_id,
            415: "Format non supporté : le fichier doit être un PDF.",
            422: "Payload métier invalide (event, type ou champs requis manquants).",
            500: "Erreur interne du serveur Akyos.",
        }
        if response.status_code != 200:
            msg = _AKYOS_ERRORS.get(
                response.status_code,
                "Erreur inattendue (HTTP %s)." % response.status_code,
            )
            _logger.error("Akyos [HTTP %s] %s : %s", response.status_code, doc_type, msg)
            raise UserError("Akyos [%s] : " % response.status_code + msg)

        _logger.info("Akyos [HTTP %s] %s envoyé avec succès : %s", response.status_code, doc_type, external_id)
        return payload


