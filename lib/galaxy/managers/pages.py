"""
Manager and Serializers for Pages.

Pages are markup created and saved by users that can contain Galaxy objects
(such as datasets) and are often used to describe or present an analysis
from within Galaxy.
"""
import logging
import re
from enum import Enum
from html.entities import name2codepoint
from html.parser import HTMLParser
from typing import (
    Callable,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Extra,
    Field,
)

from galaxy import exceptions, model
from galaxy.managers import base, sharable
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.markdown_util import (
    internal_galaxy_markdown_to_pdf,
    ready_galaxy_markdown_for_export,
    ready_galaxy_markdown_for_import,
)
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import unicodify
from galaxy.util.sanitize_html import sanitize_html

log = logging.getLogger(__name__)

# Copied from https://github.com/kurtmckee/feedparser
_cp1252 = {
    128: '\u20ac',  # euro sign
    130: '\u201a',  # single low-9 quotation mark
    131: '\u0192',  # latin small letter f with hook
    132: '\u201e',  # double low-9 quotation mark
    133: '\u2026',  # horizontal ellipsis
    134: '\u2020',  # dagger
    135: '\u2021',  # double dagger
    136: '\u02c6',  # modifier letter circumflex accent
    137: '\u2030',  # per mille sign
    138: '\u0160',  # latin capital letter s with caron
    139: '\u2039',  # single left-pointing angle quotation mark
    140: '\u0152',  # latin capital ligature oe
    142: '\u017d',  # latin capital letter z with caron
    145: '\u2018',  # left single quotation mark
    146: '\u2019',  # right single quotation mark
    147: '\u201c',  # left double quotation mark
    148: '\u201d',  # right double quotation mark
    149: '\u2022',  # bullet
    150: '\u2013',  # en dash
    151: '\u2014',  # em dash
    152: '\u02dc',  # small tilde
    153: '\u2122',  # trade mark sign
    154: '\u0161',  # latin small letter s with caron
    155: '\u203a',  # single right-pointing angle quotation mark
    156: '\u0153',  # latin small ligature oe
    158: '\u017e',  # latin small letter z with caron
    159: '\u0178',  # latin capital letter y with diaeresis
}


class PageContentFormat(str, Enum):
    markdown = "markdown"
    html = "html"


ContentFormatField: PageContentFormat = Field(
    default=PageContentFormat.html,
    title="Content format",
    description="Either `markdown` or `html`.",
)

ContentField: Optional[str] = Field(
    default="",
    title="Content",
    description="Raw text contents of the first page revision (type dependent on content_format).",
)


class PageSummaryBase(BaseModel):
    title: str = Field(
        ...,  # Required
        title="Title",
        description="The name of the page",
    )
    slug: str = Field(
        ...,  # Required
        title="Identifier",
        description="The title slug for the page URL, must be unique.",
        regex=r"^[a-z0-9\-]+$",
    )


class CreatePagePayload(PageSummaryBase):
    content_format: PageContentFormat = ContentFormatField
    content: Optional[str] = ContentField
    annotation: Optional[str] = Field(
        default=None,
        title="Annotation",
        description="Annotation that will be attached to the page.",
    )
    invocation_id: Optional[EncodedDatabaseIdField] = Field(
        None,
        title="Workflow invocation ID",
        description="Encoded ID used by workflow generated reports.",
    )

    class Config:
        use_enum_values = True  # When using .dict()
        extra = Extra.allow  # Allow any other extra fields


class PageSummary(PageSummaryBase):
    id: EncodedDatabaseIdField = Field(
        ...,  # Required
        title="ID",
        description="Encoded ID of the Page.",
    )
    model_class: str = Field(
        ...,  # Required
        title="Model class",
        description="The class of the model associated with the ID.",
        example="Page",
    )
    username: str = Field(
        ...,  # Required
        title="Username",
        description="The name of the user owning this Page.",
    )
    published: bool = Field(
        ...,  # Required
        title="Published",
        description="Whether this Page has been published.",
    )
    importable: bool = Field(
        ...,  # Required
        title="Importable",
        description="Whether this Page can be imported.",
    )
    deleted: bool = Field(
        ...,  # Required
        title="Deleted",
        description="Whether this Page has been deleted.",
    )
    latest_revision_id: EncodedDatabaseIdField = Field(
        ...,  # Required
        title="Latest revision ID",
        description="The encoded ID of the last revision of this Page.",
    )
    revision_ids: List[EncodedDatabaseIdField] = Field(
        ...,  # Required
        title="List of revisions",
        description="The history with the encoded ID of each revision of the Page.",
    )


class PageDetails(PageSummary):
    content_format: PageContentFormat = ContentFormatField
    content: Optional[str] = ContentField
    generate_version: Optional[str] = Field(
        None,
        title="Galaxy Version",
        description="The version of Galaxy this page was generated with.",
    )
    generate_time: Optional[str] = Field(
        None,
        title="Generate Date",
        description="The date this page was generated.",
    )

    class Config:
        extra = Extra.allow  # Allow any other extra fields


class PageSummaryList(BaseModel):
    __root__: List[PageSummary] = Field(
        default=[],
        title='List with summary information of Pages.',
    )


class PagesService:
    """Common interface/service logic for interactions with pages in the context of the API.

    Provides the logic of the actions invoked by API controllers and uses type definitions
    and pydantic models to declare its parameters and return types.
    """

    def __init__(self, app: MinimalManagerApp):
        self.manager = PageManager(app)
        self.serializer = PageSerializer(app)
        self.shareable_service = sharable.ShareableService(self.manager, self.serializer)

    def index(self, trans, deleted: bool = False) -> PageSummaryList:
        """Return a list of Pages viewable by the user

        :param deleted: Display deleted pages

        :rtype:     list
        :returns:   dictionaries containing summary or detailed Page information
        """
        out = []

        if trans.user_is_admin:
            r = trans.sa_session.query(model.Page)
            if not deleted:
                r = r.filter_by(deleted=False)
            for row in r:
                out.append(trans.security.encode_all_ids(row.to_dict(), recursive=True))
        else:
            # Transaction user's pages (if any)
            user = trans.user
            r = trans.sa_session.query(model.Page).filter_by(user=user)
            if not deleted:
                r = r.filter_by(deleted=False)
            for row in r:
                out.append(trans.security.encode_all_ids(row.to_dict(), recursive=True))
            # Published pages from other users
            r = trans.sa_session.query(model.Page).filter(model.Page.user != user).filter_by(published=True)
            if not deleted:
                r = r.filter_by(deleted=False)
            for row in r:
                out.append(trans.security.encode_all_ids(row.to_dict(), recursive=True))

        return PageSummaryList.parse_obj(out)

    def create(self, trans, payload: CreatePagePayload) -> PageSummary:
        """
        Create a page and return Page summary
        """
        page = self.manager.create(trans, payload.dict())
        rval = trans.security.encode_all_ids(page.to_dict(), recursive=True)
        rval['content'] = page.latest_revision.content
        self.manager.rewrite_content_for_export(trans, rval)
        return PageSummary.parse_obj(rval)

    def delete(self, trans, id: EncodedDatabaseIdField):
        """
        Deletes a page (or marks it as deleted)
        """
        page = base.get_object(trans, id, 'Page', check_ownership=True)

        # Mark a page as deleted
        page.deleted = True
        trans.sa_session.flush()

    def show(self, trans, id: EncodedDatabaseIdField) -> PageDetails:
        """View a page summary and the content of the latest revision

        :param  id:    ID of page to be displayed

        :rtype:     dict
        :returns:   Dictionary return of the Page.to_dict call with the 'content' field populated by the most recent revision
        """
        page = base.get_object(trans, id, 'Page', check_ownership=False, check_accessible=True)
        rval = trans.security.encode_all_ids(page.to_dict(), recursive=True)
        rval['content'] = page.latest_revision.content
        rval['content_format'] = page.latest_revision.content_format
        self.manager.rewrite_content_for_export(trans, rval)
        return PageDetails.parse_obj(rval)

    def show_pdf(self, trans, id: EncodedDatabaseIdField):
        """
        View a page summary and the content of the latest revision as PDF.

        :param  id: ID of page to be displayed

        :rtype: dict
        :returns: Dictionary return of the Page.to_dict call with the 'content' field populated by the most recent revision
        """
        page = base.get_object(trans, id, 'Page', check_ownership=False, check_accessible=True)
        if page.latest_revision.content_format != PageContentFormat.markdown.value:
            raise exceptions.RequestParameterInvalidException("PDF export only allowed for Markdown based pages")
        internal_galaxy_markdown = page.latest_revision.content
        trans.response.set_content_type("application/pdf")
        return internal_galaxy_markdown_to_pdf(trans, internal_galaxy_markdown, 'page')


class PageManager(sharable.SharableModelManager, UsesAnnotations):
    """Provides operations for managing a Page."""

    model_class = model.Page
    foreign_key_name = 'page'
    user_share_model = model.PageUserShareAssociation

    tag_assoc = model.PageTagAssociation
    annotation_assoc = model.PageAnnotationAssociation
    rating_assoc = model.PageRatingAssociation

    def __init__(self, app: MinimalManagerApp):
        """
        """
        super().__init__(app)
        self.workflow_manager = app.workflow_manager

    def create(self, trans, payload):
        user = trans.get_user()

        if not payload.get("title"):
            raise exceptions.ObjectAttributeMissingException("Page name is required")
        elif not payload.get("slug"):
            raise exceptions.ObjectAttributeMissingException("Page id is required")
        elif not base.is_valid_slug(payload["slug"]):
            raise exceptions.ObjectAttributeInvalidException("Page identifier must consist of only lowercase letters, numbers, and the '-' character")
        elif trans.sa_session.query(trans.app.model.Page).filter_by(user=user, slug=payload["slug"], deleted=False).first():
            raise exceptions.DuplicatedSlugException("Page identifier must be unique")

        if payload.get("invocation_id"):
            invocation_id = payload.get("invocation_id")
            invocation_report = self.workflow_manager.get_invocation_report(trans, invocation_id)
            content = invocation_report.get("markdown")
            content_format = "markdown"
        else:
            content = payload.get("content", "")
            content_format = payload.get("content_format", "html")
        content = self.rewrite_content_for_import(trans, content, content_format)

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
        page_revision.content_format = content_format
        # Persist
        session = trans.sa_session
        session.add(page)
        session.flush()
        return page

    def save_new_revision(self, trans, page, payload):
        # Assumes security has already been checked by caller.
        content = payload.get("content", None)
        content_format = payload.get("content_format", None)
        if not content:
            raise exceptions.ObjectAttributeMissingException("content undefined or empty")
        if content_format not in [None, PageContentFormat.html.value, PageContentFormat.markdown.value]:
            raise exceptions.RequestParameterInvalidException(f"content_format [{content_format}], if specified, must be either html or markdown")

        if 'title' in payload:
            title = payload['title']
        else:
            title = page.title

        if content_format is None:
            content_format = page.latest_revision.content_format
        content = self.rewrite_content_for_import(trans, content, content_format=content_format)

        page_revision = trans.app.model.PageRevision()
        page_revision.title = title
        page_revision.page = page
        page.latest_revision = page_revision
        page_revision.content = content
        page_revision.content_format = content_format

        # Persist
        session = trans.sa_session
        session.flush()
        return page_revision

    def rewrite_content_for_import(self, trans, content, content_format: str):
        if content_format == PageContentFormat.html.value:
            try:
                content = sanitize_html(content)
                processor = PageContentProcessor(trans, placeholderRenderForSave)
                processor.feed(content)
                # Output is string, so convert to unicode for saving.
                content = unicodify(processor.output(), 'utf-8')
            except exceptions.MessageException:
                raise
            except Exception:
                raise exceptions.RequestParameterInvalidException(f"problem with embedded HTML content [{content}]")
        elif content_format == PageContentFormat.markdown.value:
            content = ready_galaxy_markdown_for_import(trans, content)
        else:
            raise exceptions.RequestParameterInvalidException(f"content_format [{content_format}] must be either html or markdown")
        return content

    def rewrite_content_for_export(self, trans, as_dict):
        content = as_dict["content"]
        content_format = as_dict.get("content_format", PageContentFormat.html.value)
        if content_format == PageContentFormat.html.value:
            processor = PageContentProcessor(trans, placeholderRenderForEdit)
            processor.feed(content)
            content = unicodify(processor.output(), 'utf-8')
            as_dict["content"] = content
        elif content_format == PageContentFormat.markdown.value:
            content, extra_attributes = ready_galaxy_markdown_for_export(trans, content)
            as_dict["content"] = content
            as_dict.update(extra_attributes)
        else:
            raise exceptions.RequestParameterInvalidException(f"content_format [{content_format}] must be either html or markdown")
        return as_dict


class PageSerializer(sharable.SharableModelSerializer):
    """
    Interface/service object for serializing pages into dictionaries.
    """
    model_manager_class = PageManager
    SINGLE_CHAR_ABBR = 'p'

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.page_manager = PageManager(app)

        self.default_view = 'summary'
        self.add_view('summary', [])
        self.add_view('detailed', [])

    def add_serializers(self):
        super().add_serializers()
        self.serializers.update({
        })


class PageDeserializer(sharable.SharableModelDeserializer):
    """
    Interface/service object for validating and deserializing dictionaries
    into pages.
    """
    model_manager_class = PageManager

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.page_manager = self.manager

    def add_deserializers(self):
        super().add_deserializers()
        self.deserializers.update({
        })
        self.deserializable_keyset.update(self.deserializers.keys())


class PageContentProcessor(HTMLParser):
    """
    Processes page content to produce HTML that is suitable for display.
    For now, processor renders embedded objects.
    """
    bare_ampersand = re.compile(r"&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)")
    elements_no_end_tag = {
        'area', 'base', 'basefont', 'br', 'col', 'command', 'embed', 'frame',
        'hr', 'img', 'input', 'isindex', 'keygen', 'link', 'meta', 'param',
        'source', 'track', 'wbr'
    }

    def __init__(self, trans, render_embed_html_fn: Callable):
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
            return f"<{tag} />"
        else:
            return f"<{tag}></{tag}>"

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
            strattrs = ''.join(f' {k}="{v}"' for k, v in uattrs)
        if tag in self.elements_no_end_tag:
            self.pieces.append(f'<{tag}{strattrs} />')
        else:
            self.pieces.append(f'<{tag}{strattrs}>')

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
            self.pieces.append(f"</{tag}>")

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        # Reconstruct the original character reference.
        ref = ref.lower()
        if ref.startswith('x'):
            value = int(ref[1:], 16)
        else:
            value = int(ref)

        if value in _cp1252:
            self.pieces.append(f'&#{hex(ord(_cp1252[value]))[1:]};')
        else:
            self.pieces.append(f'&#{ref};')

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        # Reconstruct the original entity reference.
        if ref in name2codepoint or ref == 'apos':
            self.pieces.append(f'&{ref};')
        else:
            self.pieces.append(f'&amp;{ref}')

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
        self.pieces.append(f'<!--{text}-->')

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append(f'<!{text}>')

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append(f'<?{text}>')

    def output(self):
        '''Return processed HTML as a single string'''
        return ''.join(self.pieces)


PAGE_MAXRAW = 10**15


def get_page_identifiers(item_id, app):
    # Assume if item id is integer and less than 10**15, it's unencoded.
    try:
        decoded_id = int(item_id)
        if decoded_id >= PAGE_MAXRAW:
            raise ValueError("Identifier larger than maximum expected raw int, must be already encoded.")
        encoded_id = app.security.encode_id(item_id)
    except ValueError:
        # It's an encoded id.
        encoded_id = item_id
        decoded_id = base.decode_id(app, item_id)
    return (encoded_id, decoded_id)


# Utilities for encoding/decoding HTML content.
PLACEHOLDER_TEMPLATE = '''<div class="embedded-item {class_shorthand_lower} placeholder" id="{item_class}-{item_id}"><p class="title">Embedded Galaxy {class_shorthand} - '{item_name}'</p><p class="content">[Do not edit this block; Galaxy will fill it in with the annotated {class_shorthand} when it is displayed]</p></div>'''

# This is a mapping of the id portion of page contents to the cssclass/shortname.
PAGE_CLASS_MAPPING = {
    'History': 'History',
    'HistoryDatasetAssociation': 'Dataset',
    'StoredWorkflow': 'Workflow',
    'Visualization': 'Visualization'
}


def placeholderRenderForEdit(trans: ProvidesHistoryContext, item_class, item_id):
    return placeholderRenderForSave(trans, item_class, item_id, encode=True)


def placeholderRenderForSave(trans: ProvidesHistoryContext, item_class, item_id, encode=False):
    encoded_item_id, decoded_item_id = get_page_identifiers(item_id, trans.app)
    item_name = ''
    if item_class == 'History':
        history = trans.sa_session.query(model.History).get(decoded_item_id)
        history = base.security_check(trans, history, False, True)
        item_name = history.name
    elif item_class == 'HistoryDatasetAssociation':
        hda = trans.sa_session.query(model.HistoryDatasetAssociation).get(decoded_item_id)
        hda_manager = trans.app.hda_manager
        hda = hda_manager.get_accessible(decoded_item_id, trans.user)
        item_name = hda.name
    elif item_class == 'StoredWorkflow':
        wf = trans.sa_session.query(model.StoredWorkflow).get(decoded_item_id)
        wf = base.security_check(trans, wf, False, True)
        item_name = wf.name
    elif item_class == 'Visualization':
        visualization = trans.sa_session.query(model.Visualization).get(decoded_item_id)
        visualization = base.security_check(trans, visualization, False, True)
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
