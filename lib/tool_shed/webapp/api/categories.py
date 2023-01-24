import logging
from typing import (
    Any,
    Dict,
    List,
)

import tool_shed.util.shed_util_common as suc
import tool_shed_client.schema
from galaxy import (
    util,
    web,
)
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
    require_admin,
)
from galaxy.webapps.galaxy.api import depends
from tool_shed.managers.categories import CategoryManager
from tool_shed.managers.repositories import repositories_by_category
from tool_shed.webapp.model import Category
from . import BaseShedAPIController

log = logging.getLogger(__name__)


class CategoriesController(BaseShedAPIController):
    """RESTful controller for interactions with categories in the Tool Shed."""

    category_manager: CategoryManager = depends(CategoryManager)

    @expose_api
    @require_admin
    def create(self, trans, payload, **kwd):
        """
        POST /api/categories
        Return a dictionary of information about the created category.
        The following parameters are included in the payload:

        :param name (required): the name of the category
        :param description (optional): the description of the category (if not provided, the name will be used)

        Example: POST /api/categories/?key=XXXYYYXXXYYY
        Content-Disposition: form-data; name="name" Category_Name
        Content-Disposition: form-data; name="description" Category_Description
        """
        category_dict = dict(message="", status="ok")
        request = tool_shed_client.schema.CreateCategoryRequest(
            name=payload.get("name"),
            description=payload.get("description", ""),
        )
        category: Category = self.category_manager.create(trans, request)
        category_dict = self.category_manager.to_dict(category)
        category_dict["message"] = f"Category '{str(category.name)}' has been created"
        return category_dict

    @expose_api_anonymous_and_sessionless
    def get_repositories(self, trans, category_id, **kwd):
        """
        GET /api/categories/{encoded_category_id}/repositories
        Return information about the provided category and the repositories in that category.

        :param id: the encoded id of the Category object
        :param sort_key: the field by which the repositories should be sorted
        :param sort_order: ascending or descending sort
        :param page: the page number to return

        Example: GET localhost:9009/api/categories/f9cad7b01a472135/repositories
        """
        installable = util.asbool(kwd.get("installable", "false"))
        sort_key = kwd.get("sort_key", "name")
        sort_order = kwd.get("sort_order", "asc")
        page = kwd.get("page", None)
        category_dict = repositories_by_category(
            self.app,
            category_id,
            page=page,
            sort_key=sort_key,
            sort_order=sort_order,
            installable=installable,
        )
        category_dict["url"] = web.url_for(controller="categories", action="show", id=category_dict["id"])
        return category_dict

    @expose_api_anonymous_and_sessionless
    def index(self, trans, deleted=False, **kwd) -> List[Dict[str, Any]]:
        """
        GET /api/categories
        Return a list of dictionaries that contain information about each Category.

        :param deleted: flag used to include deleted categories

        Example: GET localhost:9009/api/categories
        """
        deleted = util.asbool(deleted)
        return self.category_manager.index(trans, deleted)

    @expose_api_anonymous_and_sessionless
    def show(self, trans, id, **kwd):
        """
        GET /api/categories/{encoded_category_id}
        Return a dictionary of information about a category.

        :param id: the encoded id of the Category object

        Example: GET localhost:9009/api/categories/f9cad7b01a472135
        """
        category = suc.get_category(self.app, id)
        if category is None:
            category_dict = dict(message=f"Unable to locate category record for id {str(id)}.", status="error")
            return category_dict
        category_dict = self.category_manager.to_dict(category)
        return category_dict
