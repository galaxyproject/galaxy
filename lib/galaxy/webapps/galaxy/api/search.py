"""
API for searching Galaxy Datasets
"""
import logging

from galaxy import (
    model,
    web,
)
from galaxy.exceptions import ItemAccessibilityException
from galaxy.managers.context import ProvidesUserContext
from galaxy.model.search import GalaxySearchEngine
from galaxy.util import unicodify
from galaxy.webapps.base.controller import SharableItemSecurityMixin
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class SearchController(BaseGalaxyAPIController, SharableItemSecurityMixin):
    @web.legacy_expose_api
    def create(self, trans: ProvidesUserContext, payload: dict, **kwd):
        """
        POST /api/search
        Do a search of the various elements of Galaxy.
        """
        query_txt = payload.get("query", None)
        out = []
        if query_txt is not None:
            se = GalaxySearchEngine()
            try:
                query = se.query(query_txt)
            except Exception as e:
                return {"error": unicodify(e)}
            if query is not None:
                query.decode_query_ids(trans)
                current_user_roles = trans.get_current_user_roles()
                try:
                    results = query.process(trans)
                except Exception as e:
                    return {"error": unicodify(e)}
                for item in results:
                    append = False
                    if trans.user_is_admin:
                        append = True
                    if not append:
                        if type(item) in [
                            model.LibraryFolder,
                            model.LibraryDatasetDatasetAssociation,
                            model.LibraryDataset,
                        ]:
                            if trans.app.security_agent.can_access_library_item(
                                trans.get_current_user_roles(), item, trans.user
                            ):
                                append = True
                        elif type(item) in [model.Job]:
                            if item.used_id == trans.user or trans.user_is_admin:
                                append = True
                        elif type(item) in [model.Page, model.StoredWorkflow]:
                            try:
                                if self.security_check(trans, item, False, True):
                                    append = True
                            except ItemAccessibilityException:
                                append = False
                        elif type(item) in [model.PageRevision]:
                            try:
                                if self.security_check(trans, item.page, False, True):
                                    append = True
                            except ItemAccessibilityException:
                                append = False
                        elif hasattr(item, "dataset"):
                            if trans.app.security_agent.can_access_dataset(current_user_roles, item.dataset):
                                append = True

                    if append:
                        row = query.item_to_api_value(item)
                        out.append(self.encode_all_ids(trans, row, True))
        return {"results": out}
