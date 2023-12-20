from marshmallow import fields
from odoo.addons.datamodel.core import Datamodel


class GetDatesOutputDatamodel(Datamodel):
    _name = "getdates.output.datamodel"

    date = fields.String(required=True, allow_none=False)
