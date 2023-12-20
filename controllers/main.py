from odoo.addons.base_rest.controllers import main

class AkyosRestController(main.RestController):
    _root_path = "/akyos/"
    _collection_name = "akyos.collection"
    _default_auth = "user"

