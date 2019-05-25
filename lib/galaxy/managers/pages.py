"""
Manager and Serializers for Pages.

Pages are markup created and saved by users that can contain Galaxy objects
(such as datasets) and are often used to describe or present an analysis
from within Galaxy.
"""
import logging

from galaxy import exceptions, model
from galaxy.managers import sharable
from galaxy.managers.base import is_valid_slug
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util.sanitize_html import sanitize_html

log = logging.getLogger(__name__)


class PageManager(sharable.SharableModelManager, UsesAnnotations):
    """
    """

    model_class = model.Page
    foreign_key_name = 'page'
    user_share_model = model.PageUserShareAssociation

    tag_assoc = model.PageTagAssociation
    annotation_assoc = model.PageAnnotationAssociation
    rating_assoc = model.PageRatingAssociation

    def __init__(self, app, *args, **kwargs):
        """
        """
        super(PageManager, self).__init__(app, *args, **kwargs)

    def copy(self, trans, page, user, **kwargs):
        """
        """
        pass

    def create(self, trans, payload):
        user = trans.get_user()

        if not payload.get("title", None):
            raise exceptions.ObjectAttributeMissingException("Page name is required")
        elif not payload.get("slug", None):
            raise exceptions.ObjectAttributeMissingException("Page id is required")
        elif not is_valid_slug(payload["slug"]):
            raise exceptions.ObjectAttributeInvalidException("Page identifier must consist of only lowercase letters, numbers, and the '-' character")
        elif trans.sa_session.query(trans.app.model.Page).filter_by(user=user, slug=payload["slug"], deleted=False).first():
            raise exceptions.DuplicatedSlugException("Page identifier must be unique")

        content = payload.get("content", "")
        content = sanitize_html(content)

        # Create the new stored page
        page = trans.app.model.Page()
        page.title = payload['title']
        page.slug = payload['slug']
        page_annotation = payload.get("annotation", None)
        if page_annotation is not None:
            page_annotation = sanitize_html(page_annotation)
            self.add_item_annotation(trans.sa_session, trans.get_user(), page, page_annotation)

        page.user = user
        # And the first (empty) page revision
        page_revision = trans.app.model.PageRevision()
        page_revision.title = payload['title']
        page_revision.page = page
        page.latest_revision = page_revision
        page_revision.content = content
        # Persist
        session = trans.sa_session
        session.add(page)
        session.flush()
        return page

    def save_revision(self, trans, page_id, payload):
        pass


class PageSerializer(sharable.SharableModelSerializer):
    """
    Interface/service object for serializing pages into dictionaries.
    """
    model_manager_class = PageManager
    SINGLE_CHAR_ABBR = 'p'

    def __init__(self, app):
        super(PageSerializer, self).__init__(app)
        self.page_manager = PageManager(app)

        self.default_view = 'summary'
        self.add_view('summary', [])
        self.add_view('detailed', [])

    def add_serializers(self):
        super(PageSerializer, self).add_serializers()
        self.serializers.update({
        })


class PageDeserializer(sharable.SharableModelDeserializer):
    """
    Interface/service object for validating and deserializing dictionaries
    into pages.
    """
    model_manager_class = PageManager

    def __init__(self, app):
        super(PageDeserializer, self).__init__(app)
        self.page_manager = self.manager

    def add_deserializers(self):
        super(PageDeserializer, self).add_deserializers()
        self.deserializers.update({
        })
        self.deserializable_keyset.update(self.deserializers.keys())
