from odoo import _, fields, models
from odoo.exceptions import UserError


class AegisHello(models.Model):
    _name = "aegis.hello"
    _description = "AEGIS Hello World"

    name = fields.Char(default="Hello World")

    def action_say_hello(self):
        self.env["aegis.license"].action_views_open("aegis_hello")
        raise UserError(_("Hello World from an AEGIS-protected module."))
