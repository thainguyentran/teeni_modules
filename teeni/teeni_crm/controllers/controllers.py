# -*- coding: utf-8 -*-
import base64
import sys
import time
from datetime import datetime, timedelta

import requests

from odoo import http, fields
from odoo.http import request
import logging
import json
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class TeeniCrm(http.Controller):

    @http.route('/get_warehouse', type='http', auth="user", csrf=False)
    def get_warehouse(self):
        print("Warehouse")
        _logger.exception(" ------------ Data rowsssdsddsd : %s ----------- ")

        user = request.env.user
        pickright = False
        if (user.has_group('teeni_inventory.group_packer_rights')
            and user.has_group('teeni_inventory.group_warehouse_assist_rights')
            and user.has_group('teeni_inventory.group_logistic_assist_rights')
            and user.has_group('stock.group_stock_manager')):
            pickright = True

        picking = request.env['stock.picking'].sudo().search([])
        # for rec in picking:
        #     if pickright or user.has_group('teeni_inventory.group_can_process_picking'):
        #         rec.sudo().write({"can_view": True})
        #     elif rec.picking_type_name == "Pick" and request.env.uid not in rec.packer_id.ids:
        #         rec.sudo().write({"can_view": False})
        #     else:
        #         rec.sudo().write({"can_view": True})
        true_id = []
        false_id = []
        if pickright or user.has_group('teeni_inventory.group_can_process_picking'):
            query = "update stock_picking set can_view='True' where (can_view='False' or can_view is null)"
            request._cr.execute(query)

        else:
            for rec in picking:
                if rec.picking_type_name == "Pick" and request.env.uid not in rec.packer_id.ids:
                    false_id.append(rec.id)
                    # rec.sudo().write({"can_view": False})
                else:
                    true_id.append(rec.id)
                    # rec.sudo().write({"can_view": True})
            query = "update stock_picking set can_view='True' where id in " + str(tuple(true_id))
            query += "; update stock_picking set can_view='False' where id in " + str(tuple(false_id))
            request._cr.execute(query)

            # request._cr.execute(query)

        wh = request.env['stock.warehouse'].search([])
        _logger.exception(" ------------ Data wh : %s ----------- ", wh)
        wh_list = []

        for rec in wh:
            wh_type = request.env['stock.picking.type'].search([('warehouse_id', '=', rec.id)])
            _logger.exception(" ------------ Data wh : %s ----------- ", wh_type)
            type_list = []
            for t in wh_type:
                type_list.append({
                    "picking_type_id": t.id,
                    'picking_type': t.name,
                    'count_picking_draft': t.count_picking_draft,
                    'count_picking_ready': t.count_picking_ready,
                    'count_picking_waiting': t.count_picking_waiting,
                    'count_picking_late': t.count_picking_late,
                    'count_picking_backorder': t.count_picking_backorders,
                    'count_picking_delivery': t.count_picking_delivery
                })
            wh_list.append({
                'warehouse_id': rec.id,
                "warehouse_name": rec.name,
                "data": type_list
            })
            res = {
                'status': 200, 'response': wh_list, "message": "success"}

        return json.dumps(res)

    @http.route('/get_picking_rec', type='json', auth="user", csrf=False)
    def get_picking_rec(self, **jrec):
        pick_type_list = []
        picking_type_id = 0
        is_assgin = False
        state = []
        page = None
        no_of_rec = None
        if jrec['picking_type_id']:
            picking_type_id = jrec['picking_type_id']
        if jrec['state']:
            state = jrec['state']
        if 'is_assign' in jrec.keys():
            if jrec['is_assign']:
                is_assgin = jrec['is_assign']
        print("Assign", is_assgin)
        if 'page' in jrec.keys():
            page = jrec['page']
            no_of_rec = 10
        if 'no_of_rec' in jrec.keys():
            no_of_rec = jrec['no_of_rec']
        user = request.env.user
        picking_type = request.env['stock.picking.type'].search([('id', '=', picking_type_id)])
        picking_id_lst = []
        picking_filter = []
        if picking_type.name == 'Pick':
            picking = request.env['stock.picking'].sudo().search([])

            pickright=False
            if (user.has_group('teeni_inventory.group_packer_rights')
                and user.has_group('teeni_inventory.group_warehouse_assist_rights')
                and user.has_group('teeni_inventory.group_logistic_assist_rights')
                and user.has_group('stock.group_stock_manager')):
                pickright = True

            # for rec in picking:
            #     if pickright or user.has_group('teeni_inventory.group_can_process_picking'):
            #         rec.sudo().write({"can_view": True})
            #     elif rec.picking_type_name == "Pick" and request.env.uid not in rec.packer_id.ids:
            #         rec.sudo().write({"can_view": False})
            #     else:
            #         rec.sudo().write({"can_view": True})
            true_id = []
            false_id = []
            if pickright or user.has_group('teeni_inventory.group_can_process_picking'):
                query = "update stock_picking set can_view='True' where (can_view='False' or can_view is null)"
                request._cr.execute(query)

            else:
                qry = "select * from res_users_stock_picking_rel where res_users_id='"+str(user.id)+"'"
                print("qrry", qry)
                request._cr.execute(qry)
                query_res = request._cr.dictfetchall()
                for usr in query_res:
                    picking_id_lst.append(usr["stock_picking_id"])
                picking_filter.append(tuple(['id', 'in', picking_id_lst]))
                for rec in picking:
                    if rec.picking_type_name == "Pick" and request.env.uid not in rec.packer_id.ids:
                        false_id.append(rec.id)
                        # rec.sudo().write({"can_view": False})
                    else:
                        true_id.append(rec.id)
                        # rec.sudo().write({"can_view": True})
                query = "update stock_picking set can_view='True' where id in " + str(tuple(true_id))
                request._cr.execute(query)
                query = "update stock_picking set can_view='False' where id in " + str(tuple(false_id))
                request._cr.execute(query)

        for rec in picking_type:
            if state and page and no_of_rec:
                picking_filter.append(tuple(['picking_type_id', '=', rec.id]))
                picking_filter.append(tuple(['state', '=', state]))
                print("PF1", picking_filter)
                picking = request.env['stock.picking'].sudo().search(picking_filter, offset=(page - 1) * no_of_rec, limit=no_of_rec, order="id desc")
            elif state:
                picking_filter.append(tuple(['picking_type_id', '=', rec.id]))
                picking_filter.append(tuple(['state', '=', state]))
                print("PF2", picking_filter)
                picking = request.env['stock.picking'].sudo().search(picking_filter, order="id desc")
            elif page and no_of_rec:
                picking_filter.append(tuple(['picking_type_id', '=', rec.id]))
                print("PF3", picking_filter)
                picking = request.env['stock.picking'].sudo().search(picking_filter, offset=(page - 1) * no_of_rec, limit=no_of_rec, order="id desc")
            else:
                print("PF4", picking_filter)
                picking_filter.append(tuple(['picking_type_id', '=', rec.id]))
                picking = request.env['stock.picking'].sudo().search(picking_filter, order="id desc")

            _logger.exception(" ------------ Data For  picking : %s ----------- ", picking)
            picking_list = []
            for t in picking:
                tot_rec = request.env['stock.move'].sudo().search_count([('picking_id', '=', t.id)])
                priority = ""
                if t.priority == "0":
                    priority = "Not urgent"
                elif t.priority == "1":
                    priority = "Normal"
                elif t.priority == "2":
                    priority = "Urgent"
                elif t.priority == "3":
                    priority = "Very Urgent"
                status = ""
                if t.state == "draft":
                    status = "Draft"
                elif t.state == "waiting":
                    status = "Waiting Another Operation"
                elif t.state == "confirmed":
                    status = "Waiting"
                elif t.state == "assigned":
                    # status = "Ready"
                    tot_qty_done = 0
                    # print("Qty Done", t.name,  t.move_ids_without_package.filtered(lambda l: l.picking_id == t.id).quantity_done)
                    # tot_qty_done += t.move_ids_without_package.filtered(lambda l: l.picking_id == t.id).quantity_done
                    mv = request.env['stock.move'].search([('picking_id', '=', t.id)])
                    for mvr in mv:
                        tot_qty_done += mvr.quantity_done
                    if tot_qty_done > 0:
                        status = "Partially Done"
                    else:
                        status = "Total Undone"

                elif t.state == "submitted":
                    status = "Request Submitted"
                elif t.state == "approved":
                    status = "Manager Approved"
                elif t.state == "processed":
                    status = "WH Assist Processed"
                elif t.state == "verified":
                    status = "Verified"
                elif t.state == "packed":
                    status = "Items Packed"
                elif t.state == "pack_verified":
                    status = "Packing Verified"
                elif t.state == "done" and t.is_out_for_delivery:
                    status = "Out For Delivery"
                elif t.state == "done":
                    status = "Done"
                elif t.state == "cancel":
                    status = "Cancelled"
                elif t.state == "rejected":
                    status = "Rejected"
                elif t.state == "s_rejected":
                    status = "Store Rejected"
                elif t.state == "f_delivery":
                    status = "Failed Delivery"
                elif t.state == "delivery_d":
                    status = "Failed Delivery"

                if t.picking_type_id.code == "internal" and t.date_done:
                    delivery_date = t.date_done.date().strftime("%d-%m-%Y")
                elif t.picking_type_id.code == "outgoing" and t.assigned_delivery_date:
                    delivery_date = t.assigned_delivery_date.strftime("%d-%m-%Y")
                else:
                    delivery_date = ""

                packer_name = ""
                packer = request.env['res.users'].sudo().search([('id', 'in', t.packer_id.ids)])
                for pn in packer:
                    packer_name += pn.name + ","

                if packer_name:
                    packer_name = packer_name[:-1]

                picking_list.append({
                    "picking_id": t.id if t.id else "",
                    'picking_name': t.name if t.name else "",
                    'date': t.scheduled_date.date().strftime("%d-%m-%Y") if t.scheduled_date else "",
                    'partner_id': t.partner_id.id if t.partner_id.id else 0,
                    'partner_name': t.partner_id.name if t.partner_id.name else "",
                    'origin': t.origin if t.origin else "",
                    'priority': priority if priority else "",
                    'status': status if status else "",
                    "store_code": t.store_code if t.store_code else "",
                    "store_name": t.store_name if t.store_name else "",
                    "customer_po_num": t.cus_po_num if t.cus_po_num else "",
                    "delivery_date": delivery_date if delivery_date else "",
                    "total_items": tot_rec,
                    "requested_by": t.create_uid.name,
                    "request_date": t.create_date.date().strftime("%d-%m-%Y"),
                    "packer_name": packer_name
                })
            _logger.exception(" ------------ Data For  pick_type_list : %s ----------- ", pick_type_list)
            pick_type_list.append({
                'type_id': rec.id,
                "type_name": rec.name,
                "warehouse_id": rec.warehouse_id.id,
                "warehouse_name": rec.warehouse_id.name,
                "data": picking_list
            })
        _logger.exception(" ------------ Data Last pick_type_list : %s ----------- ", pick_type_list)
        print("Pick List", pick_type_list)
        return {'status': 200, 'response': pick_type_list, "message": "success"}

    @http.route('/get_lot_no', type='json', auth="user", csrf=False)
    def get_lot_no(self, **jrec):
        lot_list = []

        product_id = 0
        if jrec['product_id']:
            product_id = jrec['product_id']
        lot = request.env['stock.production.lot'].search([('product_id', '=', product_id)])
        for rec in lot:
            lot_list.append(({
                'lot_id': rec.id,
                'lot_name': rec.name,
                'lot_qty': rec.product_qty
            }))

        print("Lot List", lot_list)
        return {'status': 200, 'response': lot_list, "message": "success"}

    @http.route('/get_user_rights', type='json', auth="user", csrf=False)
    def get_user_rights(self, **jrec):
        user_id = jrec["user_id"]
        user = request.env['res.users'].sudo().search([('id', '=', user_id)])

        packer_rights = False
        wh_assist_rights = False
        manager_rights = False
        driver_rights = False
        logistic_assist_rights = False
        admin_rights = False

        if user.has_group('teeni_inventory.group_packer_rights'):
            packer_rights = True
        if user.has_group('teeni_inventory.group_warehouse_assist_rights'):
            wh_assist_rights = True
        if user.has_group('teeni_inventory.group_manager_rights'):
            manager_rights = True
        if user.has_group('teeni_inventory.group_driver_rights'):
            driver_rights = True
        if user.has_group('teeni_inventory.group_logistic_assist_rights'):
            logistic_assist_rights = True

        if packer_rights and wh_assist_rights and manager_rights and driver_rights and logistic_assist_rights:
            admin_rights = True

        rights = {
            "Packer Rights": packer_rights,
            "WH Assist Rights": wh_assist_rights,
            "Manager Rights": manager_rights,
            "Driver Rights": driver_rights,
            "Logistic Assist Rights": logistic_assist_rights,
            "Admin Rights": admin_rights
        }

        print("Rights List", rights)
        return {'status': 200, 'response': rights, "message": "success"}

    @http.route('/insert_sign', type='json', auth="user", csrf=False)
    def insert_attachment(self, **data):
        orphan_attachment_ids = []

        record = request.env['stock.picking'].browse(data["id"])
        # authorized_fields = request.sudo()._get_form_writable_fields()

        attachment_value = {
            'name': "Signature",
            'datas': data["sign"],
            'datas_fname': "Sign",
            'res_model': "stock.picking",
            'res_id': record.id,
        }
        attachment_id = request.env['ir.attachment'].sudo().create(attachment_value)
        orphan_attachment_ids.append(attachment_id.id)
        if orphan_attachment_ids:
            values = {
                'body': _('<p>Attached Signature : </p>'),
                'model': 'stock.picking',
                'message_type': 'comment',
                'no_auto_thread': False,
                'res_id': record.id,
                'attachment_ids': [(6, 0, orphan_attachment_ids)],
            }

            request.env['mail.message'].sudo().create(values)

        return "Sign Successfully"

    @http.route('/create_backorder', type='json', auth="user", csrf=False)
    def create_backorder(self, **data):
        rec_id = data["id"]
        is_create = data["is_create"]
        pick = request.env['stock.picking'].search([('id', '=', rec_id)])

        move = request.env['stock.move'].search([('picking_id', '=', pick.id)])
        is_exist = False
        if move and pick.picking_type_id.code == "internal":
            is_exist = True
        for rec in move:
            if pick.picking_type_id.code == "internal" and rec.quantity_done == 0:
                is_exist = False
            elif rec.quantity_done > 0:
                is_exist = True

        if not is_exist and pick.picking_type_id.code == "internal":
            return {
                'status': 'Failed', "message": "Please Pack all products"
            }

        if not is_exist:
            return {
                'status': 'Failed', "message": "Please Enter Done Quantities"
            }

        bo = request.env['stock.picking'].search([('backorder_id', '=', rec_id)])
        if bo:
            return {
                'status': 'Success', "message": "Backorder Already Created"
            }
        else:
            wiz = request.env['stock.backorder.confirmation'].create({'pick_ids': [(4, p.id) for p in pick]})
            if is_create:
                wiz._process()
                return {
                    'status': 'Success', "message": "Backorder Created Successfully"
                }
            else:
                wiz._process(cancel_backorder=True)
                return {
                    'status': 'Success', "message": "No Backorder Created"
                }

    @http.route('/get_route', type='json', auth="user", csrf=False)
    def get_route(self, **data):
        rec_id = data["id"]
        pick = request.env['stock.picking'].search([('id', 'in', rec_id), ('state', '=', 'delivery')])
        url = "https://maps.googleapis.com/maps/api/directions/json?"
        # origin = 'origin=1.3321037,103.8925285'
        # destination = '&destination=1.3321037,103.8925285'
        if request.env.user.company_id.partner_id.partner_latitude == 0 or request.env.user.company_id.partner_id.partner_longitude == 0:
            return "Latitude and Longitude of warehouse is not set"

        origin = 'origin=' + str(request.env.user.company_id.partner_id.partner_latitude) + ',' + str(
            request.env.user.company_id.partner_id.partner_longitude)
        destination = '&destination=' + str(request.env.user.company_id.partner_id.partner_latitude) + ',' + str(
            request.env.user.company_id.partner_id.partner_longitude)
        way_points = '&waypoints=optimize:true'
        # key = '&key=AIzaSyBVtItvra1BiY67UwNHK_QADrwUSTAJDSg'
        get_param = request.env['ir.config_parameter'].sudo().get_param
        if get_param('google.api_key_geocode') == False:
            return "API Key for google map is not set "
        key = '&key=' + str(get_param('google.api_key_geocode'))
        print("Key", key)
        for rec in pick:
            rec.sale_id.partner_shipping_id.geo_localize()
            print("Lat Lng", rec.sale_id.partner_shipping_id.name,
                  str(rec.sale_id.partner_shipping_id.partner_latitude) + ',' + str(
                      rec.sale_id.partner_shipping_id.partner_longitude))
            if rec.sale_id.partner_shipping_id.partner_latitude == 0 or rec.sale_id.partner_shipping_id.partner_longitude == 0:
                return "Latitude and Longitude of " + str(
                    rec.sale_id.partner_shipping_id.name) + " against picking ref " + rec.name + " is not set"
            way_points = way_points + '|' + str(rec.sale_id.partner_shipping_id.partner_latitude) + ',' + str(
                rec.sale_id.partner_shipping_id.partner_longitude)

        send_url = url + origin + destination + way_points + key
        print("Send URL", send_url)
        r = requests.get(send_url)
        # if str(r) == "<Response [200]>":
        #     return "There is some error in Google Map API"
        print("Response", r)
        routes = r.json()["routes"]
        print("DATA", routes)
        if len(routes) == 0:
            return "There is some error in Google Map API"
        a_key = "legs"
        legs = [a_dict[a_key] for a_dict in routes]

        print("Legs", legs)

        way_points_order = [a_dict["waypoint_order"] for a_dict in routes]

        print("Way Point Order", way_points_order[0])

        list_do = []
        for wp in way_points_order[0]:
            print("WP", wp)
            print("REC ID", rec_id[wp])
            do = request.env['stock.picking'].search([('id', '=', rec_id[wp])])
            list_do.append({
                "picking_id": do.id if do.id else "",
                'picking_name': do.name if do.name else "",
                'date': do.scheduled_date.date().strftime("%d-%m-%Y") if do.scheduled_date else "",
                'partner_id': do.partner_id.id if do.partner_id.id else 0,
                'partner_name': do.partner_id.name if do.partner_id.name else "",
                'delivery_address': do.sale_id.partner_shipping_id.contact_address
            })
        print("Detail", list_do)
        # print("steps", legs[0])

        start_key = "start_location"
        start_loc = [a_dict[start_key] for a_dict in legs[0]]

        print("Start Location", start_loc)

        end_key = "end_location"
        end_loc = [a_dict[end_key] for a_dict in legs[0]]

        print("End Location", end_loc)

        # if "steps" in legs.keys():
        #     print("Steps", legs["steps"])

        # legs = routes["legs"]
        # print("Legs", legs)
        rtn_response = {
            "start_location": start_loc,
            "end_location": end_loc,
            "do_detail": list_do,
            "api_url": send_url
        }
        return rtn_response

    @http.route('/get_drivers', type='json', auth="user", csrf=False)
    def get_drivers(self, **data):
        pick_list = []
        if 'picking_id' in data.keys():
            picking = request.env['stock.picking'].search([('id', '=', data["picking_id"])])
            for rec in picking:
                pick_list.append({
                    "picking_id": rec.id,
                    "assigned_driver_id": rec.assigned_driver_id.id if rec.assigned_driver_id else "",
                    "assigned_driver_name": rec.assigned_driver_id.name if rec.assigned_driver_id else ""
                })

        user = request.env['res.users'].search([])
        user_list = []
        for rec in user:
            if rec.has_group('teeni_inventory.group_driver_rights'):
                user_list.append({
                    'id': rec.id,
                    'name': rec.name
                })
        print("User List", user_list)
        print("Pick List", pick_list)
        rtn_response = {
            "driver_list": user_list,
            "picking_record": pick_list
        }
        return rtn_response

    @http.route('/get_do_assign_to_drivers', type='json', auth="user", csrf=False)
    def get_do_assign_to_drivers(self, **data):
        driver_id = data["driver_id"]
        state = data["state"]
        delivery_date = data["delivery_date"]
        picking_list = []
        is_delivery = False
        if state == 'delivery':
            is_delivery = True
            state = 'done'
        print("Driver ID", driver_id, state, is_delivery)
        picking = request.env['stock.picking'].search(
            [('state', '=', state), ('assigned_driver_id', '=', driver_id), ('is_out_for_delivery', '=', is_delivery),
             ('assigned_delivery_date', '=', delivery_date)], order="id desc")
        for t in picking:
            tot_rec = request.env['stock.move'].sudo().search_count([('picking_id', '=', t.id)])
            picking_list.append({
                "picking_id": t.id if t.id else "",
                'picking_name': t.name if t.name else "",
                'date': t.assigned_delivery_date.strftime("%d-%m-%Y") if t.assigned_delivery_date else "",
                'partner_id': t.partner_id.id if t.partner_id.id else 0,
                'partner_name': t.partner_id.name if t.partner_id.name else "",
                'origin': t.origin if t.origin else "",
                'delivery_date': t.assigned_delivery_date.strftime("%d-%m-%Y") if t.assigned_delivery_date else "",
                "lat": t.sale_id.partner_shipping_id.partner_latitude,
                "lon": t.sale_id.partner_shipping_id.partner_longitude,
                "store_code": t.store_code if t.store_code else "",
                "store_name": t.store_name if t.store_name else "",
                "customer_po_num": t.cus_po_num if t.cus_po_num else "",
                "total_items": tot_rec
            })
        print("Picking List", picking_list)
        return {'status': 200, 'response': picking_list, "message": "success"}

    @http.route('/assign_driver_to_do', type='json', auth="user", csrf=False)
    def assign_driver_to_do(self, **data):

        date_time_str = '18/09/19 01:55:19'

        date_time_obj = datetime.strptime(data["delivery_date_time"], '%m-%d-%Y')

        print(date_time_obj, "DDT", data["delivery_date_time"])
        driver_id = data["driver_id"]
        picking_id = data["picking_id"]
        delivery_date_time = data["delivery_date_time"]

        picking = request.env['stock.picking'].search([('id', '=', picking_id)])
        picking.assigned_driver_id = driver_id
        picking.assigned_delivery_date = date_time_obj.date()  # datetime.strftime(datetime(delivery_date_time), "%y/%m/%d %H:%M:%S")


        if picking.sale_id:
            if picking.assigned_delivery_date >= picking.sale_id.date_order.date() + timedelta(
                days=picking.sale_id.po_term_id.days):
                return {'status': '0', 'response': "Delivery Date need to be within the PO Term.", "message": "warning"}


        # picking.write({
        #     'assigned_driver_id': driver_id,
        #     'assigned_delivery_date': delivery_date_time,
        #     'state': 'delivery'
        # })
        picking.write({
            'assigned_driver_id': driver_id,
            'assigned_delivery_date': date_time_obj.date(),
            'is_out_for_delivery':True
        })
        picking.button_validate()
        # picking.sudo().write({
        #     'assigned_driver_id': driver_id,
        #     'assigned_delivery_date': delivery_date_time
        # })
        return {'status': '1', 'response': "Driver Assigned Successfully", "message": "success"}

    @http.route('/get_customer_picking_rec', type='json', auth="user", csrf=False)
    def get_customer_picking_rec(self, **jrec):
        pick_type_list = []
        picking_type_id = 0
        is_assgin = False
        state = []
        page = None
        no_of_rec = None
        if jrec['picking_type_id']:
            picking_type_id = jrec['picking_type_id']
        if jrec['state']:
            state = jrec['state']
        if 'is_assign' in jrec.keys():
            if jrec['is_assign']:
                is_assgin = jrec['is_assign']
        print("Assign", is_assgin)
        if 'page' in jrec.keys():
            page = jrec['page']
            no_of_rec = 10
        if 'no_of_rec' in jrec.keys():
            no_of_rec = jrec['no_of_rec']

        user = request.env.user
        picking_id_lst = []
        picking_filter = []
        picking_type = request.env['stock.picking.type'].search([('id', '=', picking_type_id)])
        if picking_type.name == 'Pick':
            picking = request.env['stock.picking'].sudo().search([])

            pickright = False
            if (user.has_group('teeni_inventory.group_packer_rights')
                and user.has_group('teeni_inventory.group_warehouse_assist_rights')
                and user.has_group('teeni_inventory.group_logistic_assist_rights')
                and user.has_group('stock.group_stock_manager')):
                pickright = True

            # for rec in picking:
            #     if pickright or user.has_group('teeni_inventory.group_can_process_picking'):
            #         rec.sudo().write({"can_view": True})
            #     elif rec.picking_type_name == "Pick" and request.env.uid not in rec.packer_id.ids:
            #         rec.sudo().write({"can_view": False})
            #     else:
            #         rec.sudo().write({"can_view": True})
            true_id = []
            false_id = []
            if pickright or user.has_group('teeni_inventory.group_can_process_picking'):
                query = "update stock_picking set can_view='True' where (can_view='False' or can_view is null)"
                request._cr.execute(query)

            else:
                qry = "select * from res_users_stock_picking_rel where res_users_id='" + str(user.id) + "'"
                print("qrry", qry)
                request._cr.execute(qry)
                query_res = request._cr.dictfetchall()
                for usr in query_res:
                    picking_id_lst.append(usr["stock_picking_id"])

                for rec in picking:
                    if rec.picking_type_name == "Pick" and request.env.uid not in rec.packer_id.ids:
                        false_id.append(rec.id)
                        # rec.sudo().write({"can_view": False})
                    else:
                        true_id.append(rec.id)
                        # rec.sudo().write({"can_view": True})
                query = "update stock_picking set can_view='True' where id in " + str(tuple(true_id))
                request._cr.execute(query)
                query = "update stock_picking set can_view='False' where id in " + str(tuple(false_id))
                request._cr.execute(query)

        so = request.env['sale.order'].sudo().read_group([], fields=['partner_id'], groupby=['partner_id'])
        for rec in so:
            print("PID", rec)
            print("FFF", rec["partner_id"][0])
            picking_filter=[]
            picking_filter.append(tuple(['id', 'in', picking_id_lst]))
            if state and page and no_of_rec:
                picking_filter.append(tuple(['picking_type_id', '=', picking_type_id]))
                picking_filter.append(tuple(['state', '=', state]))
                picking_filter.append(tuple(['sale_id.partner_id', '=', rec["partner_id"][0]]))
                print("PF1", picking_filter)
                picking = request.env['stock.picking'].sudo().search(picking_filter, offset=(page - 1) * no_of_rec, limit=no_of_rec, order="id desc")
            elif state:
                picking_filter.append(tuple(['picking_type_id', '=', picking_type_id]))
                picking_filter.append(tuple(['state', '=', state]))
                picking_filter.append(tuple(['sale_id.partner_id', '=', rec["partner_id"][0]]))
                print("PF2", picking_filter)
                picking = request.env['stock.picking'].sudo().search(picking_filter, order="id desc")
            elif page and no_of_rec:
                picking_filter.append(tuple(['picking_type_id', '=', picking_type_id]))
                picking_filter.append(tuple(['sale_id.partner_id', '=', rec["partner_id"][0]]))
                print("PF3", picking_filter)
                picking = request.env['stock.picking'].sudo().search(picking_filter, offset=(page - 1) * no_of_rec, limit=no_of_rec, order="id desc")
            else:
                picking_filter.append(tuple(['picking_type_id', '=', picking_type_id]))
                picking_filter.append(tuple(['sale_id.partner_id', '=', rec["partner_id"][0]]))
                print("PF4", picking_filter)
                picking = request.env['stock.picking'].sudo().search(picking_filter, order="id desc")
            # picking = request.env['stock.picking'].search(
            #     [('picking_type_id', '=', picking_type_id), ('sale_id.partner_id', '=', rec["partner_id"][0])],
            #     order="id desc")
            # if state:
            #     picking = request.env['stock.picking'].search(
            #         [('picking_type_id', '=', picking_type_id), ('sale_id.partner_id', '=', rec["partner_id"][0]),
            #          ('state', '=', state)],
            #         order="id desc")
            _logger.exception(" ------------ Data For  picking : %s ----------- ", picking)
            picking_list = []

            for t in picking:
                # so = request.env['sale.order'].sudo().search([('partner_id', '=', t.sale_id.partner_id.id)])
                tot_rec = request.env['stock.move'].sudo().search_count([('picking_id', '=', t.id)])
                priority = ""
                if t.priority == "0":
                    priority = "Not urgent"
                elif t.priority == "1":
                    priority = "Normal"
                elif t.priority == "2":
                    priority = "Urgent"
                elif t.priority == "3":
                    priority = "Very Urgent"
                status = ""
                if t.state == "draft":
                    status = "Draft"
                elif t.state == "waiting":
                    status = "Waiting Another Operation"
                elif t.state == "confirmed":
                    status = "Waiting"
                elif t.state == "assigned":
                    # status = "Ready"
                    tot_qty_done = 0
                    # print("Qty Done", t.name,  t.move_ids_without_package.filtered(lambda l: l.picking_id == t.id).quantity_done)
                    # tot_qty_done += t.move_ids_without_package.filtered(lambda l: l.picking_id == t.id).quantity_done
                    mv = request.env['stock.move'].search([('picking_id', '=', t.id)])
                    for mvr in mv:
                        tot_qty_done += mvr.quantity_done
                    if tot_qty_done > 0:
                        status = "Partially Done"
                    else:
                        status = "Total Undone"

                elif t.state == "submitted":
                    status = "Request Submitted"
                elif t.state == "approved":
                    status = "Manager Approved"
                elif t.state == "processed":
                    status = "WH Assist Processed"
                elif t.state == "verified":
                    status = "Verified"
                elif t.state == "packed":
                    status = "Items Packed"
                elif t.state == "pack_verified":
                    status = "Packing Verified"
                elif t.state == "done" and t.is_out_for_delivery:
                    status = "Out For Delivery"
                elif t.state == "done":
                    status = "Done"
                elif t.state == "cancel":
                    status = "Cancelled"
                elif t.state == "rejected":
                    status = "Rejected"
                elif t.state == "s_rejected":
                    status = "Store Rejected"
                elif t.state == "f_delivery":
                    status = "Failed Delivery"
                elif t.state == "delivery_d":
                    status = "Failed Delivery"

                if t.picking_type_id.code == "internal" and t.date_done:
                    delivery_date = t.date_done.date().strftime("%d-%m-%Y")
                elif t.picking_type_id.code == "outgoing" and t.assigned_delivery_date:
                    delivery_date = t.assigned_delivery_date.strftime("%d-%m-%Y")
                else:
                    delivery_date = ""

                packer_name = ""
                packer = request.env['res.users'].sudo().search([('id', 'in', t.packer_id.ids)])
                for pn in packer:
                    packer_name += pn.name + ","

                if packer_name:
                    packer_name = packer_name[:-1]

                picking_list.append({
                    "picking_id": t.id if t.id else "",
                    'picking_name': t.name if t.name else "",
                    'date': t.scheduled_date.date().strftime("%d-%m-%Y") if t.scheduled_date else "",
                    'partner_id': t.partner_id.id if t.partner_id.id else 0,
                    'partner_name': t.partner_id.name if t.partner_id.name else "",
                    'origin': t.origin if t.origin else "",
                    'priority': priority if priority else "",
                    'status': status if status else "",
                    "store_code": t.store_code if t.store_code else "",
                    "store_name": t.store_name if t.store_name else "",
                    "customer_po_num": t.cus_po_num if t.cus_po_num else "",
                    "delivery_date": delivery_date if delivery_date else "",
                    "total_items": tot_rec,
                    "packer_name": packer_name
                })
            _logger.exception(" ------------ Data For  pick_type_list : %s ----------- ", pick_type_list)
            if picking_list:
                pick_type_list.append({
                    'type_id': picking_type.id,
                    "type_name": picking_type.name,
                    "customer_id": rec["partner_id"][0],
                    "customer_name": request.env['res.partner'].sudo().search([('id', '=', rec["partner_id"][0])]).name,
                    "data": picking_list
                })
        _logger.exception(" ------------ Data Last pick_type_list : %s ----------- ", pick_type_list)
        print("Pick List", pick_type_list)
        return {'status': 200, 'response': pick_type_list, "message": "success"}

    @http.route('/get_do_assign_to_drivers_by_group', type='json', auth="user", csrf=False)
    def get_do_assign_to_drivers_by_group(self, **data):
        driver_id = data["driver_id"]
        state = data["state"]
        delivery_date = data["delivery_date"]

        group_list = []

        so = request.env['sale.order'].sudo().read_group([], fields=['partner_id'], groupby=['partner_id'])
        print("SSOO", so)
        is_delivery = False
        if state == 'delivery':
            is_delivery = True
            state = 'done'
        print("Driver ID", driver_id, state, is_delivery)
        for rec in so:
            picking_list = []

            picking = request.env['stock.picking'].search(
                [('state', '=', state), ('assigned_driver_id', '=', driver_id), ('is_out_for_delivery', '=', is_delivery),
                 ('assigned_delivery_date', '=', delivery_date), ('sale_id.partner_id', '=', rec["partner_id"][0])],
                order="id desc")
            for t in picking:
                tot_rec = request.env['stock.move'].sudo().search_count([('picking_id', '=', t.id)])
                picking_list.append({
                    "picking_id": t.id if t.id else "",
                    'picking_name': t.name if t.name else "",
                    'date': t.assigned_delivery_date.strftime("%d-%m-%Y") if t.assigned_delivery_date else "",
                    'partner_id': t.partner_id.id if t.partner_id.id else 0,
                    'partner_name': t.partner_id.name if t.partner_id.name else "",
                    'origin': t.origin if t.origin else "",
                    'delivery_date': t.assigned_delivery_date.strftime("%d-%m-%Y") if t.assigned_delivery_date else "",
                    "lat": t.sale_id.partner_shipping_id.partner_latitude,
                    "lon": t.sale_id.partner_shipping_id.partner_longitude,
                    "store_code": t.store_code if t.store_code else "",
                    "store_name": t.store_name if t.store_name else "",
                    "customer_po_num": t.cus_po_num if t.cus_po_num else "",
                    "total_items": tot_rec
                })
            if picking_list:
                group_list.append({
                    "customer_id": rec["partner_id"][0],
                    "customer_name": request.env['res.partner'].sudo().search(
                        [('id', '=', rec["partner_id"][0])]).name,
                    "data": picking_list
                })
            print("Picking List", group_list)
        return {'status': 200, 'response': group_list, "message": "success"}

    @http.route('/delete_picking_items', type='http', auth="user", csrf=False)
    def delete_picking_items(self, **data):
        move_id = data["id"]
        move = request.env['stock.move'].sudo().search([('id', '=', move_id)])
        move.mapped('move_line_ids').unlink()
        if move:
            move.unlink()
        res = {"status": 200, "response": "Record Removed Successfully", "message": "success"}
        return json.dumps(res)

    @http.route('/done_all_qty', type='http', auth="user", csrf=False)
    def done_all_qty(self, **data):
        print("Data", data)
        picking_id = data["id"]
        picking = request.env['stock.picking'].sudo().search([('id', '=', picking_id)])
        for rec in picking:
            move_line = request.env['stock.move.line'].sudo().search([('picking_id', '=', rec.id), ('product_uom_qty', '!=', 0)])
            for ml in move_line:
                ml.write({'qty_done': ml.product_uom_qty})
        res = {"status": 200, "response": "All quantity done successfully", "message": "success"}
        return json.dumps(res)

    @http.route('/change_picking_state', type='json', auth="user", csrf=False)
    def change_picking_state(self, **data):
        print("Data", data)
        picking_id = data["id"]
        state = data["state"]
        if not state in ['delivery_d', 'f_delivery', 's_rejected']:
            return {"status": 200, "response": "Can only mark the DO State for Complete Delivery, Fail Delivery or Store Rejected", "message": "warning", "success": "0"}
        try:
            picking = request.env['stock.picking'].sudo().search([('id', '=', picking_id)])
            if picking:
                picking.state = state
                picking.is_out_for_delivery = False
                res = {"status": 200, "response": "Status Changed successfully", "message": "success", "success": "1"}
                return res
            else:
                res = {"status": 200, "response": "No Record Found", "message": "warning", "success": "0"}
                return res
        except Exception as e:
            print("Oops!", e.__str__(), "occurred.")
            msg = str(e.__str__())
            disallowed_characters = "'()"+ '",'+"\\" +","

            for character in disallowed_characters:
                msg = msg.replace(character, "")
            res = {"status": 200, "response": msg, "message": "warning", "success": "0"}
            return res #json.dumps(res)

        # try:
        #     picking = request.env['stock.picking'].sudo().search([('id', '=', picking_id)])
        #     picking.state = state
        #     picking.is_out_for_delivery = False
        #     res = {"status": 200, "response": "Status Changed successfully", "message": "success"}
        #     return res #json.dumps(res)
        # except Exception as e:
        #     print("Oops!", e.__str__(), "occurred.")
        #     res = {"status": 200, "response": "You don't have the permission to edit this Picking", "message": "warning"}
        #     return res #json.dumps(res)

    @http.route('/get_picking_rec_status', type='json', auth="user", csrf=False)
    def get_picking_rec_status(self, **data):
        print("Data", data)
        picking_id = data["id"]
        pick = request.env['stock.picking'].search([('id', '=', picking_id)])
        if pick:
            status = ""
            success = "0"
            if pick.is_out_for_delivery and pick.state=='done':
                status = "Out for Delivery"
                success = "1"
            elif pick.state == 'done':
                status = "Done"
            else:
                status = dict(pick._fields['state'].selection).get(pick.state)
            res = {"status": '200', "do_state": status, "message": "success", "success": success}
            return res  # json.dumps(res)
        else:
            return {"status": 200, "response": "No Record Found", "message": "warning", "success": "0"}
