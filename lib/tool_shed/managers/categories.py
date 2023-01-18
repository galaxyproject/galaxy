from typing import (
    Any,
    Callable,
    Dict,
    List,
)

import tool_shed.util.shed_util_common as suc
from galaxy import (
    exceptions,
    web,
)
from galaxy.model.base import transaction
from tool_shed.context import ProvidesUserContext
from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp.model import Category
from tool_shed_client.schema import (
    Category as CategoryResponse,
    CreateCategoryRequest,
)


class CategoryManager:
    def __init__(self, app: ToolShedApp):
        self.app = app

    def create(self, trans: ProvidesUserContext, category_request: CreateCategoryRequest) -> Category:
        name = category_request.name
        description = category_request.description or name
        if name:
            if suc.get_category_by_name(self.app, name):
                raise exceptions.Conflict("A category with that name already exists.")
            else:
                # Create the category
                category = self.app.model.Category(name=name, description=description)
                trans.sa_session.add(category)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
            return category
        else:
            raise exceptions.RequestParameterMissingException('Missing required parameter "name".')

    def index_db(self, trans: ProvidesUserContext, deleted: bool) -> List[Category]:
        category_db_objects: List[Category] = []
        if deleted and not trans.user_is_admin:
            raise exceptions.AdminRequiredException("Only administrators can query deleted categories.")
        for category in (
            trans.sa_session.query(Category).filter(Category.table.c.deleted == deleted).order_by(Category.table.c.name)
        ):
            category_db_objects.append(category)
        return category_db_objects

    def index(self, trans: ProvidesUserContext, deleted: bool) -> List[Dict[str, Any]]:
        category_dicts: List[Dict[str, Any]] = []
        for category in self.index_db(trans, deleted):
            category_dict = self.to_dict(category)
            category_dicts.append(category_dict)
        return category_dicts

    def to_dict(self, category: Category) -> Dict[str, Any]:
        category_dict = category.to_dict(view="collection", value_mapper=get_value_mapper(self.app))
        category_dict["repositories"] = self.app.repository_registry.viewable_repositories_and_suites_by_category.get(
            category.name, 0
        )
        category_dict["url"] = web.url_for(
            controller="categories", action="show", id=self.app.security.encode_id(category.id)
        )
        return category_dict

    def to_model(self, category: Category) -> CategoryResponse:
        as_dict = self.to_dict(category)
        return CategoryResponse(
            id=as_dict["id"],
            name=as_dict["name"],
            description=as_dict["description"],
            repositories=as_dict["repositories"],
        )


def get_value_mapper(app: ToolShedApp) -> Dict[str, Callable]:
    value_mapper = {"id": app.security.encode_id}
    return value_mapper
