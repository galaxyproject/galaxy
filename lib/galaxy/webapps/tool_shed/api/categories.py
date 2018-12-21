import logging

import tool_shed.util.shed_util_common as suc
from galaxy import (
    exceptions,
    util,
    web
)
from galaxy.web import (
    _future_expose_api as expose_api,
    _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless,
    require_admin as require_admin
)
from galaxy.web.base.controller import BaseAPIController
from tool_shed.util import repository_util

log = logging.getLogger(__name__)


class CategoriesController(BaseAPIController):
    """RESTful controller for interactions with categories in the Tool Shed."""

    def __get_repository_count(self, trans, category_name):
        return self.app.repository_registry.viewable_repositories_and_suites_by_category.get(category_name, 0)

    def __get_value_mapper(self, trans):
        value_mapper = {'id': trans.security.encode_id}
        return value_mapper

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
        category_dict = dict(message='', status='ok')
        name = payload.get('name', '')
        if name:
            description = payload.get('description', '')
            if not description:
                # Default the description to the name.
                description = name
            if suc.get_category_by_name(self.app, name):
                raise exceptions.Conflict('A category with that name already exists.')
            else:
                # Create the category
                category = self.app.model.Category(name=name, description=description)
                trans.sa_session.add(category)
                trans.sa_session.flush()
                category_dict = category.to_dict(view='element',
                                                 value_mapper=self.__get_value_mapper(trans))
                category_dict['message'] = "Category '%s' has been created" % str(category.name)
                category_dict['url'] = web.url_for(controller='categories',
                                                   action='show',
                                                   id=trans.security.encode_id(category.id))
        else:
            raise exceptions.RequestParameterMissingException('Missing required parameter "name".')
        return category_dict

    @expose_api_anonymous_and_sessionless
    def get_repositories(self, trans, category_id, **kwd):
        """
        GET /api/categories/{encoded_category_id}/repositories
        Return information about the provided category and the repositories in that category.

        :param id: the encoded id of the Category object

        Example: GET localhost:9009/api/categories/f9cad7b01a472135/repositories
        """
        installable = util.asbool(kwd.get('installable', 'false'))
        category = suc.get_category(self.app, category_id)
        if category is None:
            category_dict = dict(message='Unable to locate category record for id %s.' % (str(id)),
                                 status='error')
            return category_dict
        category_dict = category.to_dict(view='element',
                                         value_mapper=self.__get_value_mapper(trans))
        category_dict['url'] = web.url_for(controller='categories',
                                           action='show',
                                           id=trans.security.encode_id(category.id))
        repositories = repository_util.get_repositories_by_category(self.app, category.id, installable=installable)
        category_dict['repositories'] = repositories
        return category_dict

    @expose_api_anonymous_and_sessionless
    def index(self, trans, deleted=False, **kwd):
        """
        GET /api/categories
        Return a list of dictionaries that contain information about each Category.

        :param deleted: flag used to include deleted categories

        Example: GET localhost:9009/api/categories
        """
        category_dicts = []
        deleted = util.asbool(deleted)
        if deleted and not trans.user_is_admin:
            raise exceptions.AdminRequiredException('Only administrators can query deleted categories.')
        for category in trans.sa_session.query(self.app.model.Category) \
                                        .filter(self.app.model.Category.table.c.deleted == deleted) \
                                        .order_by(self.app.model.Category.table.c.name):
            category_dict = category.to_dict(view='collection',
                                             value_mapper=self.__get_value_mapper(trans))
            category_dict['url'] = web.url_for(controller='categories',
                                               action='show',
                                               id=trans.security.encode_id(category.id))
            category_dict['repositories'] = self.app.repository_registry.viewable_repositories_and_suites_by_category.get(category.name, 0)
            category_dicts.append(category_dict)
        return category_dicts

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
            category_dict = dict(message='Unable to locate category record for id %s.' % (str(id)),
                                 status='error')
            return category_dict
        category_dict = category.to_dict(view='element',
                                         value_mapper=self.__get_value_mapper(trans))
        category_dict['url'] = web.url_for(controller='categories',
                                           action='show',
                                           id=trans.security.encode_id(category.id))
        return category_dict
