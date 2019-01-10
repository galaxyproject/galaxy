import re
from json import loads

from markupsafe import escape
from six.moves.html_entities import name2codepoint
from six.moves.html_parser import HTMLParser
from sqlalchemy import (
    and_,
    desc,
    false,
    true
)
from sqlalchemy.orm import (
    eagerload,
    undefer
)

from galaxy import (
    managers,
    model,
    util,
    web
)
from galaxy.model.item_attrs import UsesItemRatings
from galaxy.util import unicodify
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import (
    error,
    url_for
)
from galaxy.web.base.controller import (
    BaseUIController,
    SharableMixin,
    UsesStoredWorkflowMixin,
    UsesVisualizationMixin
)
from galaxy.web.framework.helpers import (
    grids,
    time_ago
)


# Copied from https://github.com/kurtmckee/feedparser
_cp1252 = {
    128: u'\u20ac',  # euro sign
    130: u'\u201a',  # single low-9 quotation mark
    131: u'\u0192',  # latin small letter f with hook
    132: u'\u201e',  # double low-9 quotation mark
    133: u'\u2026',  # horizontal ellipsis
    134: u'\u2020',  # dagger
    135: u'\u2021',  # double dagger
    136: u'\u02c6',  # modifier letter circumflex accent
    137: u'\u2030',  # per mille sign
    138: u'\u0160',  # latin capital letter s with caron
    139: u'\u2039',  # single left-pointing angle quotation mark
    140: u'\u0152',  # latin capital ligature oe
    142: u'\u017d',  # latin capital letter z with caron
    145: u'\u2018',  # left single quotation mark
    146: u'\u2019',  # right single quotation mark
    147: u'\u201c',  # left double quotation mark
    148: u'\u201d',  # right double quotation mark
    149: u'\u2022',  # bullet
    150: u'\u2013',  # en dash
    151: u'\u2014',  # em dash
    152: u'\u02dc',  # small tilde
    153: u'\u2122',  # trade mark sign
    154: u'\u0161',  # latin small letter s with caron
    155: u'\u203a',  # single right-pointing angle quotation mark
    156: u'\u0153',  # latin small ligature oe
    158: u'\u017e',  # latin small letter z with caron
    159: u'\u0178',  # latin capital letter y with diaeresis
}


PAGE_MAXRAW = 10**15


def _get_page_identifiers(item_id, app):
    # Assume if item id is integer and less than 10**15, it's unencoded.
    try:
        decoded_id = int(item_id)
        if decoded_id >= PAGE_MAXRAW:
            raise ValueError("Identifier larger than maximum expected raw int, must be already encoded.")
        encoded_id = app.security.encode_id(item_id)
    except ValueError:
        # It's an encoded id.
        encoded_id = item_id
        decoded_id = app.security.decode_id(item_id)
    return (encoded_id, decoded_id)


def format_bool(b):
    if b:
        return "yes"
    else:
        return ""


class PageListGrid(grids.Grid):
    # Custom column.
    class URLColumn(grids.PublicURLColumn):
        def get_value(self, trans, grid, item):
            return url_for(controller='page', action='display_by_username_and_slug', username=item.user.username, slug=item.slug)

    # Grid definition
    use_panels = True
    title = "Pages"
    model_class = model.Page
    default_filter = {"published": "All", "tags": "All", "title": "All", "sharing": "All"}
    default_sort_key = "-update_time"
    columns = [
        grids.TextColumn("Title", key="title", attach_popup=True, filterable="advanced", link=(lambda item: dict(action="display_by_username_and_slug", username=item.user.username, slug=item.slug))),
        URLColumn("Public URL"),
        grids.OwnerAnnotationColumn("Annotation", key="annotation", model_annotation_association_class=model.PageAnnotationAssociation, filterable="advanced"),
        grids.IndividualTagsColumn("Tags", key="tags", model_tag_association_class=model.PageTagAssociation, filterable="advanced", grid_name="PageListGrid"),
        grids.SharingStatusColumn("Sharing", key="sharing", filterable="advanced", sortable=False),
        grids.GridColumn("Created", key="create_time", format=time_ago),
        grids.GridColumn("Last Updated", key="update_time", format=time_ago),
    ]
    columns.append(grids.MulticolFilterColumn(
        "Search",
        cols_to_filter=[columns[0], columns[2]],
        key="free-text-search", visible=False, filterable="standard"))
    global_actions = [
        grids.GridAction("Add new page", dict(controller="", action="pages/create"))
    ]
    operations = [
        grids.DisplayByUsernameAndSlugGridOperation("View", allow_multiple=False),
        grids.GridOperation("Edit content", allow_multiple=False, url_args=dict(action="edit_content")),
        grids.GridOperation("Edit attributes", allow_multiple=False, url_args=dict(controller="", action="pages/edit")),
        grids.GridOperation("Share or Publish", allow_multiple=False, condition=(lambda item: not item.deleted), url_args=dict(controller="", action="pages/sharing")),
        grids.GridOperation("Delete", confirm="Are you sure you want to delete this page?"),
    ]

    def apply_query_filter(self, trans, query, **kwargs):
        return query.filter_by(user=trans.user, deleted=False)


class PageAllPublishedGrid(grids.Grid):
    # Grid definition
    use_panels = True
    title = "Published Pages"
    model_class = model.Page
    default_sort_key = "update_time"
    default_filter = dict(title="All", username="All")
    columns = [
        grids.PublicURLColumn("Title", key="title", filterable="advanced"),
        grids.OwnerAnnotationColumn("Annotation", key="annotation", model_annotation_association_class=model.PageAnnotationAssociation, filterable="advanced"),
        grids.OwnerColumn("Owner", key="username", model_class=model.User, filterable="advanced"),
        grids.CommunityRatingColumn("Community Rating", key="rating"),
        grids.CommunityTagsColumn("Community Tags", key="tags", model_tag_association_class=model.PageTagAssociation, filterable="advanced", grid_name="PageAllPublishedGrid"),
        grids.ReverseSortColumn("Last Updated", key="update_time", format=time_ago)
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search title, annotation, owner, and tags",
            cols_to_filter=[columns[0], columns[1], columns[2], columns[4]],
            key="free-text-search", visible=False, filterable="standard")
    )

    def build_initial_query(self, trans, **kwargs):
        # See optimization description comments and TODO for tags in matching public histories query.
        return trans.sa_session.query(self.model_class).join("user").options(eagerload("user").load_only("username"), eagerload("annotations"), undefer("average_rating"))

    def apply_query_filter(self, trans, query, **kwargs):
        return query.filter(self.model_class.deleted == false()).filter(self.model_class.published == true())


class ItemSelectionGrid(grids.Grid):
    """ Base class for pages' item selection grids. """
    # Custom columns.
    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, item):
            if hasattr(item, "get_display_name"):
                return escape(item.get_display_name())
            else:
                return escape(item.name)

    # Grid definition.
    show_item_checkboxes = True
    default_filter = {"deleted": "False", "sharing": "All"}
    default_sort_key = "-update_time"
    use_paging = True
    num_rows_per_page = 10

    def apply_query_filter(self, trans, query, **kwargs):
        return query.filter_by(user=trans.user)


class HistorySelectionGrid(ItemSelectionGrid):
    """ Grid for selecting histories. """
    # Grid definition.
    title = "Saved Histories"
    model_class = model.History
    columns = [
        ItemSelectionGrid.NameColumn("Name", key="name", filterable="advanced"),
        grids.IndividualTagsColumn("Tags", key="tags", model_tag_association_class=model.HistoryTagAssociation, filterable="advanced"),
        grids.GridColumn("Last Updated", key="update_time", format=time_ago),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced"),
        grids.SharingStatusColumn("Sharing", key="sharing", filterable="advanced", sortable=False, visible=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search",
            cols_to_filter=[columns[0], columns[1]],
            key="free-text-search", visible=False, filterable="standard")
    )

    def apply_query_filter(self, trans, query, **kwargs):
        return query.filter_by(user=trans.user, purged=False)


class HistoryDatasetAssociationSelectionGrid(ItemSelectionGrid):
    """ Grid for selecting HDAs. """
    # Grid definition.
    title = "Saved Datasets"
    model_class = model.HistoryDatasetAssociation
    columns = [
        ItemSelectionGrid.NameColumn("Name", key="name", filterable="advanced"),
        grids.IndividualTagsColumn("Tags", key="tags", model_tag_association_class=model.HistoryDatasetAssociationTagAssociation, filterable="advanced"),
        grids.GridColumn("Last Updated", key="update_time", format=time_ago),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced"),
        grids.SharingStatusColumn("Sharing", key="sharing", filterable="advanced", sortable=False, visible=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search",
            cols_to_filter=[columns[0], columns[1]],
            key="free-text-search", visible=False, filterable="standard")
    )

    def apply_query_filter(self, trans, query, **kwargs):
        # To filter HDAs by user, need to join HDA and History table and then filter histories by user. This is necessary because HDAs do not have
        # a user relation.
        return query.select_from(model.HistoryDatasetAssociation.table.join(model.History.table)).filter(model.History.user == trans.user)


class WorkflowSelectionGrid(ItemSelectionGrid):
    """ Grid for selecting workflows. """
    # Grid definition.
    title = "Saved Workflows"
    model_class = model.StoredWorkflow
    columns = [
        ItemSelectionGrid.NameColumn("Name", key="name", filterable="advanced"),
        grids.IndividualTagsColumn("Tags", key="tags", model_tag_association_class=model.StoredWorkflowTagAssociation, filterable="advanced"),
        grids.GridColumn("Last Updated", key="update_time", format=time_ago),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced"),
        grids.SharingStatusColumn("Sharing", key="sharing", filterable="advanced", sortable=False, visible=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search",
            cols_to_filter=[columns[0], columns[1]],
            key="free-text-search", visible=False, filterable="standard")
    )


class PageSelectionGrid(ItemSelectionGrid):
    """ Grid for selecting pages. """
    # Grid definition.
    title = "Saved Pages"
    model_class = model.Page
    columns = [
        grids.TextColumn("Title", key="title", filterable="advanced"),
        grids.IndividualTagsColumn("Tags", key="tags", model_tag_association_class=model.PageTagAssociation, filterable="advanced"),
        grids.GridColumn("Last Updated", key="update_time", format=time_ago),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced"),
        grids.SharingStatusColumn("Sharing", key="sharing", filterable="advanced", sortable=False, visible=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search",
            cols_to_filter=[columns[0], columns[1]],
            key="free-text-search", visible=False, filterable="standard")
    )


class VisualizationSelectionGrid(ItemSelectionGrid):
    """ Grid for selecting visualizations. """
    # Grid definition.
    title = "Saved Visualizations"
    model_class = model.Visualization
    columns = [
        grids.TextColumn("Title", key="title", filterable="advanced"),
        grids.TextColumn("Type", key="type"),
        grids.IndividualTagsColumn("Tags", key="tags", model_tag_association_class=model.VisualizationTagAssociation, filterable="advanced", grid_name="VisualizationListGrid"),
        grids.SharingStatusColumn("Sharing", key="sharing", filterable="advanced", sortable=False),
        grids.GridColumn("Last Updated", key="update_time", format=time_ago),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search",
            cols_to_filter=[columns[0], columns[2]],
            key="free-text-search", visible=False, filterable="standard")
    )


# Adapted from the _BaseHTMLProcessor class of https://github.com/kurtmckee/feedparser
class _PageContentProcessor(HTMLParser, object):
    """
    Processes page content to produce HTML that is suitable for display.
    For now, processor renders embedded objects.
    """
    bare_ampersand = re.compile(r"&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)")
    elements_no_end_tag = set([
        'area', 'base', 'basefont', 'br', 'col', 'command', 'embed', 'frame',
        'hr', 'img', 'input', 'isindex', 'keygen', 'link', 'meta', 'param',
        'source', 'track', 'wbr'
    ])

    def __init__(self, trans, render_embed_html_fn):
        HTMLParser.__init__(self)
        self.trans = trans
        self.ignore_content = False
        self.num_open_tags_for_ignore = 0
        self.render_embed_html_fn = render_embed_html_fn

    def reset(self):
        self.pieces = []
        HTMLParser.reset(self)

    def _shorttag_replace(self, match):
        tag = match.group(1)
        if tag in self.elements_no_end_tag:
            return '<' + tag + ' />'
        else:
            return '<' + tag + '></' + tag + '>'

    def feed(self, data):
        data = re.compile(r'<!((?!DOCTYPE|--|\[))', re.IGNORECASE).sub(r'&lt;!\1', data)
        data = re.sub(r'<([^<>\s]+?)\s*/>', self._shorttag_replace, data)
        data = data.replace('&#39;', "'")
        data = data.replace('&#34;', '"')
        HTMLParser.feed(self, data)
        HTMLParser.close(self)

    def handle_starttag(self, tag, attrs):
        """
        Called for each start tag

        attrs is a list of (attr, value) tuples, e.g. for <pre class='screen'>,
        tag='pre', attrs=[('class', 'screen')]
        """

        # If ignoring content, just increment tag count and ignore.
        if self.ignore_content:
            self.num_open_tags_for_ignore += 1
            return

        # Not ignoring tag; look for embedded content.
        embedded_item = False
        for attribute in attrs:
            if (attribute[0] == "class") and ("embedded-item" in attribute[1].split(" ")):
                embedded_item = True
                break
        # For embedded content, set ignore flag to ignore current content and add new content for embedded item.
        if embedded_item:
            # Set processing attributes to ignore content.
            self.ignore_content = True
            self.num_open_tags_for_ignore = 1

            # Insert content for embedded element.
            for attribute in attrs:
                name = attribute[0]
                if name == "id":
                    # ID has form '<class_name>-<encoded_item_id>'
                    item_class, item_id = attribute[1].split("-")
                    embed_html = self.render_embed_html_fn(self.trans, item_class, item_id)
                    self.pieces.append(embed_html)
            return

        # Default behavior: not ignoring and no embedded content.
        uattrs = []
        strattrs = ''
        if attrs:
            for key, value in attrs:
                value = value.replace('>', '&gt;').replace('<', '&lt;').replace('"', '&quot;')
                value = self.bare_ampersand.sub("&amp;", value)
                uattrs.append((key, value))
            strattrs = ''.join(' %s="%s"' % (k, v) for k, v in uattrs)
        if tag in self.elements_no_end_tag:
            self.pieces.append('<%s%s />' % (tag, strattrs))
        else:
            self.pieces.append('<%s%s>' % (tag, strattrs))

    def handle_endtag(self, tag):
        """
        Called for each end tag

        E.g. for </pre>, tag will be 'pre'
        """
        # If ignoring content, see if current tag is the end of content to ignore.
        if self.ignore_content:
            self.num_open_tags_for_ignore -= 1
            if self.num_open_tags_for_ignore == 0:
                # Done ignoring content.
                self.ignore_content = False
            return

        # Default behavior: reconstruct the original end tag.
        if tag not in self.elements_no_end_tag:
            self.pieces.append("</%s>" % tag)

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        # Reconstruct the original character reference.
        ref = ref.lower()
        if ref.startswith('x'):
            value = int(ref[1:], 16)
        else:
            value = int(ref)

        if value in _cp1252:
            self.pieces.append('&#%s;' % hex(ord(_cp1252[value]))[1:])
        else:
            self.pieces.append('&#%s;' % ref)

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        # Reconstruct the original entity reference.
        if ref in name2codepoint or ref == 'apos':
            self.pieces.append('&%s;' % ref)
        else:
            self.pieces.append('&amp;%s' % ref)

    def handle_data(self, text):
        """
        Called for each block of plain text

        Called outside of any tag and not containing any character or entity
        references. Store the original text verbatim.
        """
        if self.ignore_content:
            return
        self.pieces.append(text)

    def handle_comment(self, text):
        # called for each HTML comment, e.g. <!-- insert Javascript code here -->
        # Reconstruct the original comment.
        self.pieces.append('<!--%s-->' % text)

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append('<!%s>' % text)

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append('<?%s>' % text)

    def output(self):
        '''Return processed HTML as a single string'''
        return ''.join(self.pieces)


class PageController(BaseUIController, SharableMixin,
                     UsesStoredWorkflowMixin, UsesVisualizationMixin, UsesItemRatings):

    _page_list = PageListGrid()
    _all_published_list = PageAllPublishedGrid()
    _history_selection_grid = HistorySelectionGrid()
    _workflow_selection_grid = WorkflowSelectionGrid()
    _datasets_selection_grid = HistoryDatasetAssociationSelectionGrid()
    _page_selection_grid = PageSelectionGrid()
    _visualization_selection_grid = VisualizationSelectionGrid()

    def __init__(self, app):
        super(PageController, self).__init__(app)
        self.history_manager = managers.histories.HistoryManager(app)
        self.history_serializer = managers.histories.HistorySerializer(self.app)
        self.hda_manager = managers.hdas.HDAManager(app)

    @web.expose
    @web.json
    @web.require_login()
    def list(self, trans, *args, **kwargs):
        """ List user's pages. """
        # Handle operation
        if 'operation' in kwargs and 'id' in kwargs:
            session = trans.sa_session
            operation = kwargs['operation'].lower()
            ids = util.listify(kwargs['id'])
            for id in ids:
                item = session.query(model.Page).get(self.decode_id(id))
                if operation == "delete":
                    item.deleted = True
            session.flush()

        # Build grid dictionary.
        grid = self._page_list(trans, *args, **kwargs)
        grid['shared_by_others'] = self._get_shared(trans)
        return grid

    @web.expose
    @web.json
    def list_published(self, trans, *args, **kwargs):
        grid = self._all_published_list(trans, *args, **kwargs)
        grid['shared_by_others'] = self._get_shared(trans)
        return grid

    def _get_shared(self, trans):
        """Identify shared pages"""
        shared_by_others = trans.sa_session \
            .query(model.PageUserShareAssociation) \
            .filter_by(user=trans.get_user()) \
            .join(model.Page.table) \
            .filter(model.Page.deleted == false()) \
            .order_by(desc(model.Page.update_time)) \
            .all()
        return [{'username' : p.page.user.username,
                 'slug'     : p.page.slug,
                 'title'    : p.page.title} for p in shared_by_others]

    @web.expose_api
    @web.require_login("create pages")
    def create(self, trans, payload=None, **kwd):
        """
        Create a new page.
        """
        if trans.request.method == 'GET':
            return {
                'title'  : 'Create a new page',
                'inputs' : [{
                    'name'      : 'title',
                    'label'     : 'Name'
                }, {
                    'name'      : 'slug',
                    'label'     : 'Identifier',
                    'help'      : 'A unique identifier that will be used for public links to this page. This field can only contain lowercase letters, numbers, and dashes (-).'
                }, {
                    'name'      : 'annotation',
                    'label'     : 'Annotation',
                    'help'      : 'A description of the page. The annotation is shown alongside published pages.'
                }]
            }
        else:
            user = trans.get_user()
            p_title = payload.get('title')
            p_slug = payload.get('slug')
            p_annotation = payload.get('annotation')
            if not p_title:
                return self.message_exception(trans, 'Please provide a page name is required.')
            elif not p_slug:
                return self.message_exception(trans, 'Please provide a unique identifier.')
            elif not self._is_valid_slug(p_slug):
                return self.message_exception(trans, 'Page identifier can only contain lowercase letters, numbers, and dashes (-).')
            elif trans.sa_session.query(model.Page).filter_by(user=user, slug=p_slug, deleted=False).first():
                return self.message_exception(trans, 'Page id must be unique.')
            else:
                # Create the new stored page
                p = model.Page()
                p.title = p_title
                p.slug = p_slug
                p.user = user
                if p_annotation:
                    p_annotation = sanitize_html(p_annotation)
                    self.add_item_annotation(trans.sa_session, user, p, p_annotation)
                # And the first (empty) page revision
                p_revision = model.PageRevision()
                p_revision.title = p_title
                p_revision.page = p
                p.latest_revision = p_revision
                p_revision.content = ""
                # Persist
                trans.sa_session.add(p)
                trans.sa_session.flush()
            return {'message': 'Page \'%s\' successfully created.' % p.title, 'status': 'success'}

    @web.expose_api
    @web.require_login("edit pages")
    def edit(self, trans, payload=None, **kwd):
        """
        Edit a page's attributes.
        """
        id = kwd.get('id')
        if not id:
            return self.message_exception(trans, 'No page id received for editing.')
        decoded_id = self.decode_id(id)
        user = trans.get_user()
        p = trans.sa_session.query(model.Page).get(decoded_id)
        if trans.request.method == 'GET':
            if p.slug is None:
                self.create_item_slug(trans.sa_session, p)
            return {
                'title'  : 'Edit page attributes',
                'inputs' : [{
                    'name'      : 'title',
                    'label'     : 'Name',
                    'value'     : p.title
                }, {
                    'name'      : 'slug',
                    'label'     : 'Identifier',
                    'value'     : p.slug,
                    'help'      : 'A unique identifier that will be used for public links to this page. This field can only contain lowercase letters, numbers, and dashes (-).'
                }, {
                    'name'      : 'annotation',
                    'label'     : 'Annotation',
                    'value'     : self.get_item_annotation_str(trans.sa_session, user, p),
                    'help'      : 'A description of the page. The annotation is shown alongside published pages.'
                }]
            }
        else:
            p_title = payload.get('title')
            p_slug = payload.get('slug')
            p_annotation = payload.get('annotation')
            if not p_title:
                return self.message_exception(trans, 'Please provide a page name is required.')
            elif not p_slug:
                return self.message_exception(trans, 'Please provide a unique identifier.')
            elif not self._is_valid_slug(p_slug):
                return self.message_exception(trans, 'Page identifier can only contain lowercase letters, numbers, and dashes (-).')
            elif p_slug != p.slug and trans.sa_session.query(model.Page).filter_by(user=p.user, slug=p_slug, deleted=False).first():
                return self.message_exception(trans, 'Page id must be unique.')
            else:
                p.title = p_title
                p.slug = p_slug
                if p_annotation:
                    p_annotation = sanitize_html(p_annotation)
                    self.add_item_annotation(trans.sa_session, user, p, p_annotation)
                trans.sa_session.add(p)
                trans.sa_session.flush()
            return {'message': 'Attributes of \'%s\' successfully saved.' % p.title, 'status': 'success'}

    @web.expose
    @web.require_login("edit pages")
    def edit_content(self, trans, id):
        """
        Render the main page editor interface.
        """
        id = self.decode_id(id)
        page = trans.sa_session.query(model.Page).get(id)
        assert page.user == trans.user
        content = page.latest_revision.content
        processor = _PageContentProcessor(trans, _placeholderRenderForEdit)
        processor.feed(content)
        content = unicodify(processor.output(), 'utf-8')
        return trans.fill_template("page/editor.mako", page=page, content=content)

    @web.expose
    @web.require_login("use Galaxy pages")
    def share(self, trans, id, email="", use_panels=False):
        """ Handle sharing with an individual user. """
        msg = mtype = None
        page = trans.sa_session.query(model.Page).get(self.decode_id(id))
        if email:
            other = trans.sa_session.query(model.User) \
                                    .filter(and_(model.User.table.c.email == email,
                                                 model.User.table.c.deleted == false())) \
                                    .first()
            if not other:
                mtype = "error"
                msg = ("User '%s' does not exist" % escape(email))
            elif other == trans.get_user():
                mtype = "error"
                msg = ("You cannot share a page with yourself")
            elif trans.sa_session.query(model.PageUserShareAssociation) \
                    .filter_by(user=other, page=page).count() > 0:
                mtype = "error"
                msg = ("Page already shared with '%s'" % escape(email))
            else:
                share = model.PageUserShareAssociation()
                share.page = page
                share.user = other
                session = trans.sa_session
                session.add(share)
                self.create_item_slug(session, page)
                session.flush()
                page_title = escape(page.title)
                other_email = escape(other.email)
                trans.set_message("Page '%s' shared with user '%s'" % (page_title, other_email))
                return trans.response.send_redirect(url_for("/pages/sharing?id=%s" % id))
        return trans.fill_template("/ind_share_base.mako",
                                   message=msg,
                                   messagetype=mtype,
                                   item=page,
                                   email=email,
                                   use_panels=use_panels)

    @web.expose
    @web.require_login()
    def save(self, trans, id, content, annotations):
        id = self.decode_id(id)
        page = trans.sa_session.query(model.Page).get(id)
        assert page.user == trans.user

        # Sanitize content
        content = sanitize_html(content)
        processor = _PageContentProcessor(trans, _placeholderRenderForSave)
        processor.feed(content)
        # Output is string, so convert to unicode for saving.
        content = unicodify(processor.output(), 'utf-8')

        # Add a new revision to the page with the provided content.
        page_revision = model.PageRevision()
        page_revision.title = page.title
        page_revision.page = page
        page.latest_revision = page_revision
        page_revision.content = content

        # Save annotations.
        annotations = loads(annotations)
        for annotation_dict in annotations:
            item_id = self.decode_id(annotation_dict['item_id'])
            item_class = self.get_class(annotation_dict['item_class'])
            item = trans.sa_session.query(item_class).filter_by(id=item_id).first()
            if not item:
                raise RuntimeError("cannot find annotated item")
            text = sanitize_html(annotation_dict['text'])

            # Add/update annotation.
            if item_id and item_class and text:
                # Get annotation association.
                annotation_assoc_class = eval("model.%sAnnotationAssociation" % item_class.__name__)
                annotation_assoc = trans.sa_session.query(annotation_assoc_class).filter_by(user=trans.get_user())
                if item_class == model.History.__class__:
                    annotation_assoc = annotation_assoc.filter_by(history=item)
                elif item_class == model.HistoryDatasetAssociation.__class__:
                    annotation_assoc = annotation_assoc.filter_by(hda=item)
                elif item_class == model.StoredWorkflow.__class__:
                    annotation_assoc = annotation_assoc.filter_by(stored_workflow=item)
                elif item_class == model.WorkflowStep.__class__:
                    annotation_assoc = annotation_assoc.filter_by(workflow_step=item)
                annotation_assoc = annotation_assoc.first()
                if not annotation_assoc:
                    # Create association.
                    annotation_assoc = annotation_assoc_class()
                    item.annotations.append(annotation_assoc)
                    annotation_assoc.user = trans.get_user()
                # Set annotation user text.
                annotation_assoc.annotation = text
        trans.sa_session.flush()

    @web.expose
    @web.require_login()
    def display(self, trans, id):
        id = self.decode_id(id)
        page = trans.sa_session.query(model.Page).get(id)
        if not page:
            raise web.httpexceptions.HTTPNotFound()
        return self.display_by_username_and_slug(trans, page.user.username, page.slug)

    @web.expose
    def display_by_username_and_slug(self, trans, username, slug):
        """ Display page based on a username and slug. """

        # Get page.
        session = trans.sa_session
        user = session.query(model.User).filter_by(username=username).first()
        page = trans.sa_session.query(model.Page).filter_by(user=user, slug=slug, deleted=False).first()
        if page is None:
            raise web.httpexceptions.HTTPNotFound()
        # Security check raises error if user cannot access page.
        self.security_check(trans, page, False, True)

        # Process page content.
        processor = _PageContentProcessor(trans, self._get_embed_html)
        processor.feed(page.latest_revision.content)
        # Output is string, so convert to unicode for display.
        page_content = unicodify(processor.output(), 'utf-8')

        # Get rating data.
        user_item_rating = 0
        if trans.get_user():
            user_item_rating = self.get_user_item_rating(trans.sa_session, trans.get_user(), page)
            if user_item_rating:
                user_item_rating = user_item_rating.rating
            else:
                user_item_rating = 0
        ave_item_rating, num_ratings = self.get_ave_item_rating_data(trans.sa_session, page)

        return trans.fill_template_mako("page/display.mako", item=page,
                                        item_data=page_content,
                                        user_item_rating=user_item_rating,
                                        ave_item_rating=ave_item_rating,
                                        num_ratings=num_ratings,
                                        content_only=True)

    @web.expose
    @web.require_login("use Galaxy pages")
    def set_accessible_async(self, trans, id=None, accessible=False):
        """ Set page's importable attribute and slug. """
        page = self.get_page(trans, id)

        # Only set if importable value would change; this prevents a change in the update_time unless attribute really changed.
        importable = accessible in ['True', 'true', 't', 'T']
        if page.importable != importable:
            if importable:
                self._make_item_accessible(trans.sa_session, page)
            else:
                page.importable = importable
            trans.sa_session.flush()
        return

    @web.expose
    @web.require_login("rate items")
    @web.json
    def rate_async(self, trans, id, rating):
        """ Rate a page asynchronously and return updated community data. """

        page = self.get_page(trans, id, check_ownership=False, check_accessible=True)
        if not page:
            return trans.show_error_message("The specified page does not exist.")

        # Rate page.
        self.rate_item(trans.sa_session, trans.get_user(), page, rating)

        return self.get_ave_item_rating_data(trans.sa_session, page)

    @web.expose
    def get_embed_html_async(self, trans, id):
        """ Returns HTML for embedding a workflow in a page. """

        # TODO: user should be able to embed any item he has access to. see display_by_username_and_slug for security code.
        page = self.get_page(trans, id)
        if page:
            return "Embedded Page '%s'" % page.title

    @web.expose
    @web.json
    @web.require_login("use Galaxy pages")
    def get_name_and_link_async(self, trans, id=None):
        """ Returns page's name and link. """
        page = self.get_page(trans, id)

        if self.create_item_slug(trans.sa_session, page):
            trans.sa_session.flush()
        return_dict = {"name": page.title, "link": url_for(controller='page',
                                                           action="display_by_username_and_slug",
                                                           username=page.user.username,
                                                           slug=page.slug)}
        return return_dict

    @web.expose
    @web.json
    @web.require_login("select a history from saved histories")
    def list_histories_for_selection(self, trans, **kwargs):
        """ Returns HTML that enables a user to select one or more histories. """
        return self._history_selection_grid(trans, **kwargs)

    @web.expose
    @web.json
    @web.require_login("select a workflow from saved workflows")
    def list_workflows_for_selection(self, trans, **kwargs):
        """ Returns HTML that enables a user to select one or more workflows. """
        return self._workflow_selection_grid(trans, **kwargs)

    @web.expose
    @web.json
    @web.require_login("select a visualization from saved visualizations")
    def list_visualizations_for_selection(self, trans, **kwargs):
        """ Returns HTML that enables a user to select one or more visualizations. """
        return self._visualization_selection_grid(trans, **kwargs)

    @web.expose
    @web.json
    @web.require_login("select a page from saved pages")
    def list_pages_for_selection(self, trans, **kwargs):
        """ Returns HTML that enables a user to select one or more pages. """
        return self._page_selection_grid(trans, **kwargs)

    @web.expose
    @web.json
    @web.require_login("select a dataset from saved datasets")
    def list_datasets_for_selection(self, trans, **kwargs):
        """ Returns HTML that enables a user to select one or more datasets. """
        return self._datasets_selection_grid(trans, **kwargs)

    @web.expose
    def get_editor_iframe(self, trans):
        """ Returns the document for the page editor's iframe. """
        return trans.fill_template("page/wymiframe.mako")

    def get_page(self, trans, id, check_ownership=True, check_accessible=False):
        """Get a page from the database by id."""
        # Load history from database
        id = self.decode_id(id)
        page = trans.sa_session.query(model.Page).get(id)
        if not page:
            error("Page not found")
        else:
            return self.security_check(trans, page, check_ownership, check_accessible)

    def get_item(self, trans, id):
        return self.get_page(trans, id)

    def _get_embedded_history_html(self, trans, decoded_id):
        """
        Returns html suitable for embedding in another page.
        """
        # histories embedded in pages are set to importable when embedded, check for access here
        history = self.history_manager.get_accessible(decoded_id, trans.user, current_history=trans.history)

        # create ownership flag for template, dictify models
        # note: adding original annotation since this is published - get_dict returns user-based annos
        user_is_owner = trans.user == history.user
        history.annotation = self.get_item_annotation_str(trans.sa_session, history.user, history)

        # include all datasets: hidden, deleted, and purged
        history_dictionary = self.history_serializer.serialize_to_view(
            history, view='detailed', user=trans.user, trans=trans
        )
        contents = self.history_serializer.serialize_contents(history, 'contents', trans=trans, user=trans.user)
        history_dictionary['annotation'] = history.annotation

        filled = trans.fill_template("history/embed.mako",
                                     item=history,
                                     user_is_owner=user_is_owner,
                                     history_dict=history_dictionary,
                                     content_dicts=contents)
        return filled

    def _get_embedded_visualization_html(self, trans, encoded_id):
        """
        Returns html suitable for embedding visualizations in another page.
        """
        visualization = self.get_visualization(trans, encoded_id, False, True)
        visualization.annotation = self.get_item_annotation_str(trans.sa_session, visualization.user, visualization)
        if not visualization:
            return None

        # Fork to template based on visualization.type (registry or builtin).
        if((trans.app.visualizations_registry and visualization.type in trans.app.visualizations_registry.plugins) and
                (visualization.type not in trans.app.visualizations_registry.BUILT_IN_VISUALIZATIONS)):
            # if a registry visualization, load a version into an iframe :(
            # TODO: simplest path from A to B but not optimal - will be difficult to do reg visualizations any other way
            # TODO: this will load the visualization twice (once above, once when the iframe src calls 'saved')
            encoded_visualization_id = trans.security.encode_id(visualization.id)
            return trans.fill_template('visualization/embed_in_frame.mako',
                                       item=visualization,
                                       encoded_visualization_id=encoded_visualization_id,
                                       content_only=True)

        return trans.fill_template("visualization/embed.mako", item=visualization, item_data=None)

    def _get_embed_html(self, trans, item_class, item_id):
        """ Returns HTML for embedding an item in a page. """
        item_class = self.get_class(item_class)
        encoded_id, decoded_id = _get_page_identifiers(item_id, trans.app)
        if item_class == model.History:
            return self._get_embedded_history_html(trans, decoded_id)

        elif item_class == model.HistoryDatasetAssociation:
            dataset = self.hda_manager.get_accessible(decoded_id, trans.user)
            dataset = self.hda_manager.error_if_uploading(dataset)

            dataset.annotation = self.get_item_annotation_str(trans.sa_session, dataset.history.user, dataset)
            if dataset:
                data = self.hda_manager.text_data(dataset)
                return trans.fill_template("dataset/embed.mako", item=dataset, item_data=data)

        elif item_class == model.StoredWorkflow:
            workflow = self.get_stored_workflow(trans, encoded_id, False, True)
            workflow.annotation = self.get_item_annotation_str(trans.sa_session, workflow.user, workflow)
            if workflow:
                self.get_stored_workflow_steps(trans, workflow)
                return trans.fill_template("workflow/embed.mako", item=workflow, item_data=workflow.latest_workflow.steps)

        elif item_class == model.Visualization:
            return self._get_embedded_visualization_html(trans, encoded_id)

        elif item_class == model.Page:
            pass


PLACEHOLDER_TEMPLATE = '''<div class="embedded-item {class_shorthand_lower} placeholder" id="{item_class}-{item_id}"><p class="title">Embedded Galaxy {class_shorthand} - '{item_name}'</p><p class="content">[Do not edit this block; Galaxy will fill it in with the annotated {class_shorthand} when it is displayed]</p></div>'''

# This is a mapping of the id portion of page contents to the cssclass/shortname.
PAGE_CLASS_MAPPING = {
    'History': 'History',
    'HistoryDatasetAssociation': 'Dataset',
    'StoredWorkflow': 'Workflow',
    'Visualization': 'Visualization'
}


def _placeholderRenderForEdit(trans, item_class, item_id):
    return _placeholderRenderForSave(trans, item_class, item_id, encode=True)


def _placeholderRenderForSave(trans, item_class, item_id, encode=False):
    encoded_item_id, decoded_item_id = _get_page_identifiers(item_id, trans.app)
    item_name = ''
    if item_class == 'History':
        history = trans.sa_session.query(trans.model.History).get(decoded_item_id)
        history = managers.base.security_check(trans, history, False, True)
        item_name = history.name
    elif item_class == 'HistoryDatasetAssociation':
        hda = trans.sa_session.query(trans.model.HistoryDatasetAssociation).get(decoded_item_id)
        hda_manager = managers.hdas.HDAManager(trans.app)
        hda = hda_manager.get_accessible(decoded_item_id, trans.user)
        item_name = hda.name
    elif item_class == 'StoredWorkflow':
        wf = trans.sa_session.query(trans.model.StoredWorkflow).get(decoded_item_id)
        wf = managers.base.security_check(trans, wf, False, True)
        item_name = wf.name
    elif item_class == 'Visualization':
        visualization = trans.sa_session.query(trans.model.Visualization).get(decoded_item_id)
        visualization = managers.base.security_check(trans, visualization, False, True)
        item_name = visualization.title
    class_shorthand = PAGE_CLASS_MAPPING[item_class]
    if encode:
        item_id = encoded_item_id
    else:
        item_id = decoded_item_id
    return PLACEHOLDER_TEMPLATE.format(
        item_class=item_class,
        class_shorthand=class_shorthand,
        class_shorthand_lower=class_shorthand.lower(),
        item_id=item_id,
        item_name=item_name
    )
