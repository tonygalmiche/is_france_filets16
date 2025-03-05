from typing import Annotated, List, Union
from fastapi import APIRouter, Depends, Form, Header   # type: ignore # Documentation FastAPI : https://fastapi.tiangolo.com/tutorial/ et https://github.com/OCA/rest-framework/tree/16.0/fastapi
from pydantic import BaseModel                         # type: ignore
from odoo import api, fields, models                   # type: ignore
from odoo.api import Environment                       # type: ignore
from odoo.addons.fastapi.dependencies import odoo_env  # type: ignore
import passlib                                         # type: ignore
import uuid 


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app: str = fields.Selection(
        selection_add=[("akyos", "API REST pour Akyos")], ondelete={"akyos": "cascade"}
    )

    def _get_fastapi_routers(self):
        if self.app == "akyos":
            return [akyos_api_router]
        return super()._get_fastapi_routers()


akyos_api_router = APIRouter()


class DateModel(BaseModel):
    date: str


def verif_token(env, token):
    users = env['res.users'].search([('is_token_api','=',token)])
    test=False
    for user in users:
        if user == env.user:
            return ""
    return {"err": "Accès non autorisé !"}


@akyos_api_router.post("/auth/login")
def auth_login(
    env     : Annotated[Environment, Depends(odoo_env)],
    login   : Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    uid = env['res.users'].authenticate(env['res.users'], login,password, {'interactive':False})
    if not uid:
        return {"Status": "Error", "Message": "Incorrect username or password"}
    assert password
    env.cr.execute(
        "SELECT COALESCE(password, '') FROM res_users WHERE id=%s" % uid
    )
    [hashed] = env.cr.fetchone()
    valid, replacement = passlib.context.CryptContext(
        ['pbkdf2_sha512', 'plaintext'],
        deprecated=['plaintext'],
    ).verify_and_update(password, hashed)
    if not valid:
        return {"Status": "Error", "Message": "Incorrect username or password"}
    if valid:
        user = env['res.users'].browse(uid)
        token =  uuid.uuid4() 
        user.sudo().is_token_api = token
        return {
            "status": "success",
            "token" : token,
            "session": {"sid":token}, # Pour compatibilité avec ancienne API Akyos
        }


@akyos_api_router.get("/api-rest/get-dates/{departement}/{limite}") #, response_model=List[DateModel])
def get_dates(
        env: Annotated[Environment, Depends(odoo_env)],
        departement: int,
        limite: int,
        X_Openerp_Session_Id: Annotated[Union[str, None], Header()] = None,
    ):
    """
    Retourne la liste des dates disponibles pour un département
    """
    res=verif_token(env, X_Openerp_Session_Id)
    if res!="":
        return res
    dates = env['is.departement'].get_dates(departement, limite)
    res=[]
    for date in dates:
        res.append(DateModel(date=date.strftime('%Y-%m-%d')))
    return res


@akyos_api_router.post("/api-rest/create-order")
def create_order(
    env           : Annotated[Environment, Depends(odoo_env)],
    code_client   : Annotated[str, Form()],
    departement   : Annotated[str, Form()],
    zone          : Annotated[str, Form()],
    tarif_ht      : Annotated[str, Form()],
    montant_paye  : Annotated[str, Form()],
    date_reservee : Annotated[str, Form()],
    prestation    : Annotated[str, Form()],
    nom_chantier  : Annotated[str, Form()],

    complement_info_chantier   : Annotated[str, Form()] = None,
    adresse_chantier           : Annotated[str, Form()] = None,
    complement_adresse_chantier: Annotated[str, Form()] = None,
    cp_chantier                : Annotated[str, Form()] = None,
    ville_chantier             : Annotated[str, Form()] = None,

    utilisateur   : Annotated[str, Form()] = None,
    ref_client    : Annotated[str, Form()] = None,
    superficie    : Annotated[str, Form()] = None,
    piece_jointe1 : Annotated[str, Form()] = None,
    piece_jointe2 : Annotated[str, Form()] = None,
    piece_jointe3 : Annotated[str, Form()] = None,
    piece_jointe4 : Annotated[str, Form()] = None,
    piece_jointe5 : Annotated[str, Form()] = None,
    X_Openerp_Session_Id: Annotated[Union[str, None], Header()] = None,
): 
    res=verif_token(env, X_Openerp_Session_Id)
    if res!="":
        return res
    

    res=env['sale.order'].create_akyos_order(
        code_client   = code_client, 
        departement   = departement, 
        zone          = zone, 
        tarif_ht      = tarif_ht, 
        montant_paye  = montant_paye, 
        date_reservee = date_reservee, 
        prestation    = prestation,
        nom_chantier  = nom_chantier, 

        complement_info_chantier     = complement_info_chantier, 
        adresse_chantier             = adresse_chantier, 
        complement_adresse_chantier  = complement_adresse_chantier, 
        cp_chantier                  = cp_chantier, 
        ville_chantier               = ville_chantier, 

        utilisateur   = utilisateur,
        ref_client    = ref_client,
        superficie    = superficie,
        piece_jointe1 = piece_jointe1,
        piece_jointe2 = piece_jointe2,
        piece_jointe3 = piece_jointe3,
        piece_jointe4 = piece_jointe4,
        piece_jointe5 = piece_jointe5,
    )
    return res


@akyos_api_router.post("/api-rest/create-depose")
def create_depose(
    env          : Annotated[Environment, Depends(odoo_env)],
    numcde       : Annotated[str, Form()],
    departement  : Annotated[str, Form()],
    date_reservee: Annotated[str, Form()],
    X_Openerp_Session_Id: Annotated[Union[str, None], Header()] = None,
): 
    res=verif_token(env, X_Openerp_Session_Id)
    if res!="":
        return res
    res = env['sale.order'].create_akyos_depose(
        numcde        = numcde, 
        departement   = departement, 
        date_reservee = date_reservee,
    )
    return res


@akyos_api_router.post("/api-rest/update-dates")
def update_dates(
    env        : Annotated[Environment, Depends(odoo_env)],
    numcde     : Annotated[str, Form()],
    date_pose  : Annotated[str, Form()] = None,
    date_depose: Annotated[str, Form()] = None,
    X_Openerp_Session_Id: Annotated[Union[str, None], Header()] = None,
): 
    res=verif_token(env, X_Openerp_Session_Id)
    if res!="":
        return res
    res = env['sale.order'].update_dates_akyos(
        numcde      = numcde, 
        date_pose   = date_pose, 
        date_depose = date_depose,
    )
    return res


@akyos_api_router.post("/auth/logout")
def auth_logout(
    env  : Annotated[Environment, Depends(odoo_env)],
    X_Openerp_Session_Id: Annotated[Union[str, None], Header()] = None,
):
    res=verif_token(env, X_Openerp_Session_Id)
    if res!="":
        return res
    token = X_Openerp_Session_Id
    users = env['res.users'].search([('is_token_api','=',token)])
    for user in users:
        user.sudo().is_token_api = False
    return {
        "status": "logout",
    }



