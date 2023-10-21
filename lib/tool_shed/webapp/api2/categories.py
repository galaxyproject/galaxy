from typing import (
    List,
    Optional,
)

from fastapi import Body

from tool_shed.context import SessionRequestContext
from tool_shed.managers.categories import CategoryManager
from tool_shed.managers.repositories import repositories_by_category
from tool_shed_client.schema import (
    Category as CategoryResponse,
    CreateCategoryRequest,
    RepositoriesByCategory,
)
from . import (
    CategoryIdPathParam,
    CategoryRepositoriesInstallableQueryParam,
    CategoryRepositoriesPageQueryParam,
    CategoryRepositoriesSortKeyQueryParam,
    CategoryRepositoriesSortOrderQueryParam,
    depends,
    DependsOnTrans,
    Router,
)

router = Router(tags=["categories"])


@router.cbv
class FastAPICategories:
    category_manager: CategoryManager = depends(CategoryManager)

    @router.post(
        "/api/categories",
        description="create a category",
        operation_id="categories__create",
        require_admin=True,
    )
    def create(
        self, trans: SessionRequestContext = DependsOnTrans, request: CreateCategoryRequest = Body(...)
    ) -> CategoryResponse:
        category = self.category_manager.create(trans, request)
        return self.category_manager.to_model(category)

    @router.get(
        "/api/categories",
        description="index category",
        operation_id="categories__index",
    )
    def index(self, trans: SessionRequestContext = DependsOnTrans) -> List[CategoryResponse]:
        """
        Return a list of dictionaries that contain information about each Category.
        """
        deleted = False
        categories = self.category_manager.index_db(trans, deleted)
        return [self.category_manager.to_model(c) for c in categories]

    @router.get(
        "/api/categories/{encoded_category_id}",
        description="show category",
        operation_id="categories__show",
    )
    def show(self, encoded_category_id: str = CategoryIdPathParam) -> CategoryResponse:
        """
        Return a list of dictionaries that contain information about each Category.
        """
        category = self.category_manager.get(encoded_category_id)
        return self.category_manager.to_model(category)

    @router.get(
        "/api/categories/{encoded_category_id}/repositories",
        description="display repositories by category",
        operation_id="categories__repositories",
    )
    def repositories(
        self,
        trans: SessionRequestContext = DependsOnTrans,
        encoded_category_id: str = CategoryIdPathParam,
        installable: bool = CategoryRepositoriesInstallableQueryParam,
        sort_key: str = CategoryRepositoriesSortKeyQueryParam,
        sort_order: str = CategoryRepositoriesSortOrderQueryParam,
        page: Optional[int] = CategoryRepositoriesPageQueryParam,
    ) -> RepositoriesByCategory:
        return repositories_by_category(
            trans.app,
            encoded_category_id,
            page=page,
            sort_key=sort_key,
            sort_order=sort_order,
            installable=installable,
        )
