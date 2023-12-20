from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component
from odoo.http import request


class AkyosService(Component):
    _inherit = "base.rest.service"
    _name = "akyos.service"
    _usage = "api-rest"
    _collection = "akyos.collection"
    _description = "API REST pour Akyos"


    @restapi.method(
        [(["/get-dates/<string:departement>/<int:limite>"], "GET")],
        output_param=Datamodel("getdates.output.datamodel", is_list=True),
        auth="user",
    )
    def get_dates(self, departement, limite):
        """
        Retourne la liste des dates disponibles pour un département
        """
        dates = self.env['is.departement'].get_dates(departement, limite)
        Datamodel = self.env.datamodels["getdates.output.datamodel"]
        res=[]
        for date in dates:
            res.append(Datamodel(date=date.strftime('%Y-%m-%d')))
        return res


    @restapi.method(
        [(["/create-order"], "POST")],
        auth="user",
    )
    def create_order(self):
        "create_order"
        params = request.params
        vals={}
        for a in params:
            vals[a]=params[a]
        res=self.env['sale.order'].create_akyos_order(
            code_client   = vals.get("code_client"), 
            departement   = vals.get("departement"), 
            zone          = vals.get("zone"), 
            tarif_ht      = vals.get("tarif_ht"), 
            montant_paye  = vals.get("montant_paye"), 
            date_reservee = vals.get("date_reservee"), 
            prestation    = vals.get("prestation"),
            nom_chantier  = vals.get("nom_chantier"), 
            utilisateur   = vals.get("utilisateur")
        )
        return res


    @restapi.method(
        [(["/create-depose"], "POST")],
        auth="user",
    )
    def create_depose(self):
        "create_depose"
        params = request.params
        vals={}
        for a in params:
            vals[a]=params[a]
        res = self.env['sale.order'].create_akyos_depose(
            numcde        = vals.get("numcde"), 
            departement   = vals.get("departement"), 
            date_reservee = vals.get("date_reservee")
        )
        return res

