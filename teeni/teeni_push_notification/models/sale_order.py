import json
import logging
import re
import time
import threading
import uuid

import itertools
import requests
from html2text import html2text
from requests.exceptions import ConnectionError
from odoo import api, fields, models, _
from odoo.modules.registry import Registry

FCM_MESSAGES_LIMIT = 1000
FCM_END_POINT = "https://fcm.googleapis.com/fcm/send"
FCM_RETRY_ATTEMPT = 2
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        super(SaleOrder, self).action_confirm()
        for order in self:
            self._push_notify_confirm_sale(
                _('Get an order %s from %s' % (order.name, order.partner_id.name)))
        return True

    def _get_default_fcm_credentials(self):
        return self.env['res.config.settings'].sudo().get_fcm_credentials()

    def _push_notify_confirm_sale(self, message):
        mobile_ids = self.env['sale.push_device'].sudo().search(
            []).mapped('mobile_id')
        if len(mobile_ids) > 0:
            mobile_ids_chunks = [mobile_ids[i:i+FCM_MESSAGES_LIMIT]
                                 for i in range(0, len(mobile_ids), FCM_MESSAGES_LIMIT)]
            for mobile_ids_smaller_chunk in mobile_ids_chunks:
                fcm_api_key = self._get_default_fcm_credentials()[
                    'fcm_api_key']
                threaded_sending = threading.Thread(target=self._fcm_send_notification, args=(
                    mobile_ids_smaller_chunk,
                    fcm_api_key,
                    message
                ))
                threaded_sending.start()
        else:
            _logger.info("There is no device to push notification.")

    def _fcm_send_notification(self, mobile_ids, fcm_api_key, message, attempt=1):
        if not fcm_api_key:
            _logger.exception("You need a FCM API key to send notification")
            return

        payload = {
            'subject': 'Sale Order Confirmed',
            'body': message
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": "key=" + fcm_api_key,
        }
        data = {
            'data': payload,
            'registration_ids': mobile_ids,
            'priority': 'high',
            'content_available': True,
            # ios not supporting background push notification without notification data
            'notification': {
                'title': payload['subject'],
                'body': payload['body'],
                'sound': 'default',

            },
        }

        _logger.info('Prepare to send request push notification')

        try:
            response = requests.post(
                FCM_END_POINT, headers=headers, data=json.dumps(data))
            json_data = json.loads(response.text)

            if response.status_code == 200 or json_data['failure'] != 1:
                # res = self._fcm_process_response(response, subscription_ids)
                _logger.info('Response from Firebase:')
                _logger.info(json_data)
            elif response.status_code == 401:
                _logger.warning(
                    "FCM Authentication: Provide valid FCM api key")
            elif response.status_code == 400:
                _logger.warning("Invalid JSON: Invalid payload format")
            else:
                retry = self._fcm_calculate_retry_after(response.headers)
                if retry and attempt <= FCM_RETRY_ATTEMPT:
                    _logger.warning("FCM Service Unavailable: retrying")
                    time.sleep(retry)
                    attempt = attempt + 1
                    self._fcm_send_notification(
                        mobile_ids, fcm_api_key, message, attempt=attempt)
                else:
                    _logger.warning(
                        "FCM service not available try after some time")
        except ConnectionError:
            _logger.warning("No Internet connection")
        except Exception:
            _logger.warning("Failed processing FCM queue")

    def _fcm_calculate_retry_after(self, response_headers):
        retry_after = response_headers.get('Retry-After')

        if retry_after:
            # Parse from seconds (e.g. Retry-After: 120)
            if type(retry_after) is int:
                return retry_after
            # Parse from HTTP-Date (e.g. Retry-After: Fri, 31 Dec 1999 23:59:59 GMT)
            else:
                try:
                    from email.utils import parsedate
                    from calendar import timegm
                    return timegm(parsedate(retry_after))
                except (TypeError, OverflowError, ValueError):
                    return None
        return None
