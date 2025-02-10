from typing import (
    Any,
    Callable,
    Dict,
    List,
)

from sqlalchemy import select

import tool_shed.util.shed_util_common as suc
from galaxy import (
    exceptions,
    web,
)
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

    def get(self, encoded_category_id: str) -> Category:
        return suc.get_category(self.app, encoded_category_id)

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
                trans.sa_session.commit()
            return category
        else:
            raise exceptions.RequestParameterMissingException('Missing required parameter "name".')

    def index_db(self, trans: ProvidesUserContext, deleted: bool) -> List[Category]:
        if deleted and not trans.user_is_admin:
            raise exceptions.AdminRequiredException("Only administrators can query deleted categories.")
        return list(get_categories_by_deleted(trans.sa_session, deleted))

    def index(self, trans: ProvidesUserContext, deleted: bool) -> List[Dict[str, Any]]:
        category_dicts: List[Dict[str, Any]] = []
        for category in self.index_db(trans, deleted):
            category_dict = self.to_dict(category)
            category_dicts.append(category_dict)
        return category_dicts

    def to_dict(self, category: Category) -> Dict[str, Any]:
        category_dict = category.to_dict(view="collection", value_mapper=get_value_mapper(self.app))
        category_dict["repositories"] = category.active_repository_count()
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
            deleted=as_dict["deleted"],
        )


def get_value_mapper(app: ToolShedApp) -> Dict[str, Callable]:
    value_mapper = {"id": app.security.encode_id}
    return value_mapper


def get_categories_by_deleted(session, deleted):
    stmt = select(Category).where(Category.deleted == deleted).order_by(Category.name)
    return session.scalars(stmt)
