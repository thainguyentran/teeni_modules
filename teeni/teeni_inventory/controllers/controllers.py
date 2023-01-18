# -*- coding: utf-8 -*-
from odoo import http

# class TeeniInventory(http.Controller):
#     @http.route('/teeni_inventory/teeni_inventory/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/teeni_inventory/teeni_inventory/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('teeni_inventory.listing', {
#             'root': '/teeni_inventory/teeni_inventory',
#             'objects': http.request.env['teeni_inventory.teeni_inventory'].search([]),
#         })

#     @http.route('/teeni_inventory/teeni_inventory/objects/<model("teeni_inventory.teeni_inventory"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('teeni_inventory.object', {
#             'object': obj
#         })