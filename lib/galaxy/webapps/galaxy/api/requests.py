"""
API operations on a sample tracking system.
"""
import logging

from sqlalchemy import and_, false

from galaxy import exceptions
from galaxy import web
from galaxy.util.bunch import Bunch
from galaxy.web import url_for
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class RequestsAPIController(BaseAPIController):
    _update_types = Bunch(REQUEST='request_state')
    _update_type_values = [v[1] for v in _update_types.items()]

    @web.expose_api
    def index(self, trans, **kwd):
        """
        GET /api/requests
        Displays a collection (list) of sequencing requests.
        """
        if not trans.app.config.enable_legacy_sample_tracking_api:
            trans.response.status = 403
            return "The configuration of this Galaxy instance does not allow accessing this API."
        # if admin user then return all requests
        if trans.user_is_admin():
            query = trans.sa_session.query(trans.app.model.Request) \
                .filter(trans.app.model.Request.table.c.deleted == false())\
                .all()
        else:
            query = trans.sa_session.query(trans.app.model.Request)\
                .filter(and_(trans.app.model.Request.table.c.user_id == trans.user.id and
                trans.app.model.Request.table.c.deleted == false())) \
                .all()
        rval = []
        for request in query:
            item = request.to_dict()
            item['url'] = url_for('requests', id=trans.security.encode_id(request.id))
            item['id'] = trans.security.encode_id(item['id'])
            if trans.user_is_admin():
                item['user'] = request.user.email
            rval.append(item)
        return rval

    @web.expose_api
    def show(self, trans, id, **kwd):
        """
        GET /api/requests/{encoded_request_id}
        Displays details of a sequencing request.
        """
        if not trans.app.config.enable_legacy_sample_tracking_api:
            trans.response.status = 403
            return "The configuration of this Galaxy instance does not allow accessing this API."
        try:
            request_id = trans.security.decode_id(id)
        except TypeError:
            trans.response.status = 400
            return "Malformed id ( %s ) specified, unable to decode." % (str(id))
        try:
            request = trans.sa_session.query(trans.app.model.Request).get(request_id)
        except Exception:
            request = None
        if not request or not (trans.user_is_admin() or request.user.id == trans.user.id):
            trans.response.status = 400
            return "Invalid request id ( %s ) specified." % str(request_id)
        item = request.to_dict()
        item['url'] = url_for('requests', id=trans.security.encode_id(request.id))
        item['id'] = trans.security.encode_id(item['id'])
        item['user'] = request.user.email
        item['num_of_samples'] = len(request.samples)
        return item

    @web.expose_api
    def update(self, trans, id, key, payload, **kwd):
        """
        PUT /api/requests/{encoded_request_id}
        Updates a request state, sample state or sample dataset transfer status
        depending on the update_type
        """
        if not trans.app.config.enable_legacy_sample_tracking_api:
            trans.response.status = 403
            return "The configuration of this Galaxy instance does not allow accessing this API."
        update_type = None
        if 'update_type' not in payload:
            trans.response.status = 400
            return "Missing required 'update_type' parameter.  Please consult the API documentation for help."
        else:
            update_type = payload.pop('update_type')
        if update_type not in self._update_type_values:
            trans.response.status = 400
            return "Invalid value for 'update_type' parameter ( %s ) specified.  Please consult the API documentation for help." % update_type
        try:
            request_id = trans.security.decode_id(id)
        except TypeError:
            trans.response.status = 400
            return "Malformed  request id ( %s ) specified, unable to decode." % str(id)
        try:
            request = trans.sa_session.query(trans.app.model.Request).get(request_id)
        except Exception:
            request = None
        if not request or not (trans.user_is_admin() or request.user.id == trans.user.id):
            trans.response.status = 400
            return "Invalid request id ( %s ) specified." % str(request_id)
        # check update type
        if update_type == 'request_state':
            # Make sure all the samples of the current request have the same state
            common_state = request.samples_have_common_state
            if not common_state:
                # If the current request state is complete and one of its samples moved from
                # the final sample state, then move the request state to In-progress
                if request.is_complete:
                    message = "At least 1 sample state moved from the final sample state, so now the request's state is (%s)" % request.states.SUBMITTED
                    event = trans.model.RequestEvent(request, request.states.SUBMITTED, message)
                    trans.sa_session.add(event)
                    trans.sa_session.flush()
            else:
                final_state = False
                request_type_state = request.type.final_sample_state
                if common_state.id == request_type_state.id:
                    # since all the samples are in the final state, change the request state to 'Complete'
                    comment = "All samples of this sequencing request are in the final sample state (%s). " % request_type_state.name
                    state = request.states.COMPLETE
                    final_state = True
                else:
                    comment = "All samples of this sequencing request are in the (%s) sample state. " % common_state.name
                    state = request.states.SUBMITTED
                event = trans.model.RequestEvent(request, state, comment)
                trans.sa_session.add(event)
                trans.sa_session.flush()
                # See if an email notification is configured to be sent when the samples are in this state.
                retval = request.send_email_notification(trans, common_state, final_state)
                if retval:
                    message = comment + retval
                else:
                    message = comment
            return 200, message
