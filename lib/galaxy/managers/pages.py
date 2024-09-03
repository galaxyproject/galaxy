"""
Manager and Serializers for Pages.

Pages are markup created and saved by users that can contain Galaxy objects
(such as datasets) and are often used to describe or present an analysis
from within Galaxy.
"""

import logging
import re
from html.entities import name2codepoint
from html.parser import HTMLParser
from typing import (
    Callable,
    Optional,
    Tuple,
)

import sqlalchemy
from sqlalchemy import (
    desc,
    false,
    func,
    or_,
    select,
    true,
)
from sqlalchemy.orm import aliased

from galaxy import (
    exceptions,
    model,
)
from galaxy.managers import (
    base,
    sharable,
)
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.markdown_util import (
    ready_galaxy_markdown_for_export,
    ready_galaxy_markdown_for_import,
)
from galaxy.model import (
    History,
    HistoryDatasetAssociation,
    Page,
    PageRevision,
    PageTagAssociation,
    PageUserShareAssociation,
    StoredWorkflow,
    User,
    Visualization,
)
from galaxy.model.base import transaction
from galaxy.model.index_filter_util import (
    append_user_filter,
    raw_text_column_filter,
    tag_filter,
    text_column_filter,
)
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.schema import (
    CreatePagePayload,
    PageContentFormat,
    PageIndexQueryPayload,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import unicodify
from galaxy.util.sanitize_html import sanitize_html
from galaxy.util.search import (
    FilteredTerm,
    parse_filters_structured,
    RawTextTerm,
)

log = logging.getLogger(__name__)

# Copied from https://github.com/kurtmckee/feedparser
_cp1252 = {
    128: "\u20ac",  # euro sign
    130: "\u201a",  # single low-9 quotation mark
    131: "\u0192",  # latin small letter f with hook
    132: "\u201e",  # double low-9 quotation mark
    133: "\u2026",  # horizontal ellipsis
    134: "\u2020",  # dagger
    135: "\u2021",  # double dagger
    136: "\u02c6",  # modifier letter circumflex accent
    137: "\u2030",  # per mille sign
    138: "\u0160",  # latin capital letter s with caron
    139: "\u2039",  # single left-pointing angle quotation mark
    140: "\u0152",  # latin capital ligature oe
    142: "\u017d",  # latin capital letter z with caron
    145: "\u2018",  # left single quotation mark
    146: "\u2019",  # right single quotation mark
    147: "\u201c",  # left double quotation mark
    148: "\u201d",  # right double quotation mark
    149: "\u2022",  # bullet
    150: "\u2013",  # en dash
    151: "\u2014",  # em dash
    152: "\u02dc",  # small tilde
    153: "\u2122",  # trade mark sign
    154: "\u0161",  # latin small letter s with caron
    155: "\u203a",  # single right-pointing angle quotation mark
    156: "\u0153",  # latin small ligature oe
    158: "\u017e",  # latin small letter z with caron
    159: "\u0178",  # latin capital letter y with diaeresis
}

INDEX_SEARCH_FILTERS = {
    "title": "title",
    "slug": "slug",
    "tag": "tag",
    "user": "user",
    "u": "user",
    "s": "slug",
    "t": "tag",
    "is": "is",
}


class PageManager(sharable.SharableModelManager, UsesAnnotations):
    """Provides operations for managing a Page."""

    model_class = model.Page
    foreign_key_name = "page"
    user_share_model = model.PageUserShareAssociation

    tag_assoc = model.PageTagAssociation
    annotation_assoc = model.PageAnnotationAssociation
    rating_assoc = model.PageRatingAssociation

    def __init__(self, app: MinimalManagerApp):
        """ """
        super().__init__(app)
        self.workflow_manager = app.workflow_manager

    def index_query(
        self, trans: ProvidesUserContext, payload: PageIndexQueryPayload, include_total_count: bool = False
    ) -> Tuple[sqlalchemy.engine.Result, int]:
        show_deleted = payload.deleted
        show_own = payload.show_own
        show_published = payload.show_published
        show_shared = payload.show_shared
        is_admin = trans.user_is_admin
        user = trans.user

        if show_shared and show_deleted and not is_admin:
            message = "show_shared and show_deleted cannot both be specified as true"
            raise exceptions.RequestParameterInvalidException(message)

        if not user and not show_published:
            message = "Requires user to log in."
            raise exceptions.RequestParameterInvalidException(message)

        stmt = select(self.model_class)

        filters = []
        if show_own or (not show_published and not show_shared and not is_admin):
            filters = [self.model_class.user == user]
        if show_published:
            filters.append(self.model_class.published == true())
        if user and show_shared:
            filters.append(self.user_share_model.user == user)
            stmt = stmt.outerjoin(self.model_class.users_shared_with)
        stmt = stmt.where(or_(*filters))

        if payload.user_id:
            stmt = stmt.where(self.model_class.user_id == payload.user_id)

        if payload.search:
            search_query = payload.search
            parsed_search = parse_filters_structured(search_query, INDEX_SEARCH_FILTERS)

            def p_tag_filter(term_text: str, quoted: bool):
                nonlocal stmt
                alias = aliased(PageTagAssociation)
                stmt = stmt.outerjoin(Page.tags.of_type(alias))
                return tag_filter(alias, term_text, quoted)

            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    q = term.text
                    if key == "tag":
                        pg = p_tag_filter(term.text, term.quoted)
                        stmt = stmt.where(pg)
                    elif key == "title":
                        stmt = stmt.where(text_column_filter(Page.title, term))
                    elif key == "slug":
                        stmt = stmt.where(text_column_filter(Page.slug, term))
                    elif key == "user":
                        stmt = append_user_filter(stmt, Page, term)
                    elif key == "is":
                        if q == "deleted":
                            show_deleted = True
                        if q == "published":
                            stmt = stmt.where(Page.published == true())
                        if q == "importable":
                            stmt = stmt.where(Page.importable == true())
                        elif q == "shared_with_me":
                            if not show_shared:
                                message = "Can only use tag is:shared_with_me if show_shared parameter also true."
                                raise exceptions.RequestParameterInvalidException(message)
                            stmt = stmt.where(PageUserShareAssociation.user == user)
                elif isinstance(term, RawTextTerm):
                    tf = p_tag_filter(term.text, False)
                    alias = aliased(User)
                    stmt = stmt.outerjoin(Page.user.of_type(alias))
                    stmt = stmt.where(
                        raw_text_column_filter(
                            [
                                Page.title,
                                Page.slug,
                                tf,
                                alias.username,
                            ],
                            term,
                        )
                    )

        if (show_published or show_shared) and not is_admin:
            show_deleted = False

        stmt = stmt.where(self.model_class.deleted == (true() if show_deleted else false())).distinct()

        if include_total_count:
            total_matches = get_count(trans.sa_session, stmt)
        else:
            total_matches = None
        sort_column = getattr(Page, payload.sort_by)
        if payload.sort_desc:
            sort_column = sort_column.desc()
        stmt = stmt.order_by(sort_column)
        if payload.limit is not None:
            stmt = stmt.limit(payload.limit)
        if payload.offset is not None:
            stmt = stmt.offset(payload.offset)
        return trans.sa_session.scalars(stmt), total_matches  # type:ignore[return-value]

    def create_page(self, trans, payload: CreatePagePayload):
        user = trans.get_user()

        if not payload.title:
            raise exceptions.ObjectAttributeMissingException("Page name is required")
        elif not payload.slug:
            raise exceptions.ObjectAttributeMissingException("Page id is required")
        elif not base.is_valid_slug(payload.slug):
            raise exceptions.ObjectAttributeInvalidException(
                "Page identifier must consist of only lowercase letters, numbers, and the '-' character"
            )
        elif page_exists(trans.sa_session, user, payload.slug):
            raise exceptions.DuplicatedSlugException("Page identifier must be unique")

        if payload.invocation_id:
            invocation_id = payload.invocation_id
            invocation_report = self.workflow_manager.get_invocation_report(trans, invocation_id)
            content = invocation_report.get("markdown")
            content_format = "markdown"
        else:
            content = payload.content
            content_format = payload.content_format
        content = self.rewrite_content_for_import(trans, content, content_format)

        # Create the new stored page
        page = trans.app.model.Page()
        page.title = payload.title
        page.slug = payload.slug
        if (page_annotation := payload.annotation) is not None:
            page_annotation = sanitize_html(page_annotation)
            self.add_item_annotation(trans.sa_session, trans.get_user(), page, page_annotation)

        page.user = user
        # And the first (empty) page revision
        page_revision = trans.app.model.PageRevision()
        page_revision.title = payload.title
        page_revision.page = page
        page.latest_revision = page_revision
        page_revision.content = content
        page_revision.content_format = content_format
        # Persist
        session = trans.sa_session
        session.add(page)
        with transaction(session):
            session.commit()
        return page

    def save_new_revision(self, trans, page, payload):
        # Assumes security has already been checked by caller.
        content = payload.get("content", None)
        content_format = payload.get("content_format", None)
        if not content:
            raise exceptions.ObjectAttributeMissingException("content undefined or empty")
        if content_format not in [None, PageContentFormat.html.value, PageContentFormat.markdown.value]:
            raise exceptions.RequestParameterInvalidException(
                f"content_format [{content_format}], if specified, must be either html or markdown"
            )

        if "title" in payload:
            title = payload["title"]
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
        with transaction(session):
            session.commit()
        return page_revision

    def rewrite_content_for_import(self, trans, content, content_format: str):
        if content_format == PageContentFormat.html.value:
            try:
                content = sanitize_html(content)
                processor = PageContentProcessor(trans, placeholderRenderForSave)
                processor.feed(content)
                # Output is string, so convert to unicode for saving.
                content = unicodify(processor.output(), "utf-8")
            except exceptions.MessageException:
                raise
            except Exception:
                raise exceptions.RequestParameterInvalidException(f"problem with embedded HTML content [{content}]")
        elif content_format == PageContentFormat.markdown.value:
            content = ready_galaxy_markdown_for_import(trans, content)
        else:
            raise exceptions.RequestParameterInvalidException(
                f"content_format [{content_format}] must be either html or markdown"
            )
        return content

    def rewrite_content_for_export(self, trans, as_dict):
        content = as_dict["content"]
        content_format = as_dict.get("content_format", PageContentFormat.html.value)
        if content_format == PageContentFormat.html.value:
            processor = PageContentProcessor(trans, placeholderRenderForEdit)
            processor.feed(content)
            content = unicodify(processor.output(), "utf-8")
            as_dict["content"] = content
        elif content_format == PageContentFormat.markdown.value:
            content, extra_attributes = ready_galaxy_markdown_for_export(trans, content)
            as_dict["content"] = content
            as_dict.update(extra_attributes)
        else:
            raise exceptions.RequestParameterInvalidException(
                f"content_format [{content_format}] must be either html or markdown"
            )
        return as_dict


class PageSerializer(sharable.SharableModelSerializer):
    """
    Interface/service object for serializing pages into dictionaries.
    """

    model_manager_class = PageManager
    SINGLE_CHAR_ABBR = "p"

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.page_manager = PageManager(app)

        self.default_view = "summary"
        self.add_view("summary", [])
        self.add_view("detailed", [])

    def add_serializers(self):
        super().add_serializers()
        self.serializers.update({})


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
        self.deserializers.update({})
        self.deserializable_keyset.update(self.deserializers.keys())


class PageContentProcessor(HTMLParser):
    """
    Processes page content to produce HTML that is suitable for display.
    For now, processor renders embedded objects.
    """

    bare_ampersand = re.compile(r"&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)")
    elements_no_end_tag = {
        "area",
        "base",
        "basefont",
        "br",
        "col",
        "command",
        "embed",
        "frame",
        "hr",
        "img",
        "input",
        "isindex",
        "keygen",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
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
        data = re.compile(r"<!((?!DOCTYPE|--|\[))", re.IGNORECASE).sub(r"&lt;!\1", data)
        data = re.sub(r"<([^<>\s]+?)\s*/>", self._shorttag_replace, data)
        data = data.replace("&#39;", "'")
        data = data.replace("&#34;", '"')
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
        strattrs = ""
        if attrs:
            for key, value in attrs:
                value = value.replace(">", "&gt;").replace("<", "&lt;").replace('"', "&quot;")
                value = self.bare_ampersand.sub("&amp;", value)
                uattrs.append((key, value))
            strattrs = "".join(f' {k}="{v}"' for k, v in uattrs)
        if tag in self.elements_no_end_tag:
            self.pieces.append(f"<{tag}{strattrs} />")
        else:
            self.pieces.append(f"<{tag}{strattrs}>")

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
        if ref.startswith("x"):
            value = int(ref[1:], 16)
        else:
            value = int(ref)

        if value in _cp1252:
            self.pieces.append(f"&#{hex(ord(_cp1252[value]))[1:]};")
        else:
            self.pieces.append(f"&#{ref};")

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        # Reconstruct the original entity reference.
        if ref in name2codepoint or ref == "apos":
            self.pieces.append(f"&{ref};")
        else:
            self.pieces.append(f"&amp;{ref}")

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
        self.pieces.append(f"<!--{text}-->")

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append(f"<!{text}>")

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append(f"<?{text}>")

    def output(self):
        """Return processed HTML as a single string"""
        return "".join(self.pieces)


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
PLACEHOLDER_TEMPLATE = """<div class="embedded-item {class_shorthand_lower} placeholder" id="{item_class}-{item_id}"><p class="title">Embedded Galaxy {class_shorthand} - '{item_name}'</p><p class="content">[Do not edit this block; Galaxy will fill it in with the annotated {class_shorthand} when it is displayed]</p></div>"""

# This is a mapping of the id portion of page contents to the cssclass/shortname.
PAGE_CLASS_MAPPING = {
    "History": "History",
    "HistoryDatasetAssociation": "Dataset",
    "StoredWorkflow": "Workflow",
    "Visualization": "Visualization",
}


def placeholderRenderForEdit(trans: ProvidesHistoryContext, item_class, item_id):
    return placeholderRenderForSave(trans, item_class, item_id, encode=True)


def placeholderRenderForSave(trans: ProvidesHistoryContext, item_class, item_id, encode=False):
    encoded_item_id, decoded_item_id = get_page_identifiers(item_id, trans.app)
    item_name: Optional[str] = ""
    if item_class == "History":
        history = trans.sa_session.get(History, decoded_item_id)
        history = base.security_check(trans, history, False, True)
        assert history
        item_name = history.name
    elif item_class == "HistoryDatasetAssociation":
        hda = trans.sa_session.get(HistoryDatasetAssociation, decoded_item_id)
        hda_manager = trans.app.hda_manager
        hda = hda_manager.get_accessible(decoded_item_id, trans.user)
        assert hda
        item_name = hda.name
    elif item_class == "StoredWorkflow":
        wf = trans.sa_session.get(StoredWorkflow, decoded_item_id)
        wf = base.security_check(trans, wf, False, True)
        assert wf
        item_name = wf.name
    elif item_class == "Visualization":
        visualization = trans.sa_session.get(Visualization, decoded_item_id)
        visualization = base.security_check(trans, visualization, False, True)
        assert visualization
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
        item_name=item_name,
    )


def get_page_revision(session: galaxy_scoped_session, page_id: int):
    stmt = select(PageRevision).filter_by(page_id=page_id)
    return session.scalars(stmt)


def get_shared_pages(session: galaxy_scoped_session, user: User):
    stmt = (
        select(PageUserShareAssociation)
        .where(PageUserShareAssociation.user == user)
        .join(Page)
        .where(Page.deleted == false())
        .order_by(desc(Page.update_time))
    )
    return session.scalars(stmt)


def get_page(session: galaxy_scoped_session, user: User, slug: str):
    stmt = _build_page_query(select(Page), user, slug)
    return session.scalars(stmt).first()


def page_exists(session: galaxy_scoped_session, user: User, slug: str) -> bool:
    stmt = _build_page_query(select(Page.id), user, slug)
    return session.scalars(stmt).first() is not None


def _build_page_query(select_clause, user: User, slug: str):
    return select_clause.where(Page.user == user).where(Page.slug == slug).where(Page.deleted == false()).limit(1)


def get_count(session, statement):
    stmt = select(func.count()).select_from(statement)
    return session.scalar(stmt)
