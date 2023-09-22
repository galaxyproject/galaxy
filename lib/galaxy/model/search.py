"""
The GQL (Galaxy Query Language) search engine parsers a simple 'SQL-Like' query
syntax to obtain items from the Galaxy installations.
Rather then allow/force the user to do queries on the Galaxy schema, it uses
a small set of 'Views' which are simple table representations of complex galaxy ideas.
So while a history and its tags may exist in seperate tables in the real schema, in
GQL they exist in the same view

Example Queries:

select name, id, file_size from hda

select name from hda

select name, model_class from ldda

select * from history

select * from workflow

select id, name from history where name='Unnamed history'

select * from history where name='Unnamed history'

"""

import logging
import re
from json import dumps
from typing import Dict

import parsley
from sqlalchemy import and_
from sqlalchemy.orm import aliased

from galaxy.model import (
    ExtendedMetadata,
    ExtendedMetadataIndex,
    History,
    HistoryAnnotationAssociation,
    HistoryDatasetAssociation,
    HistoryDatasetAssociationTagAssociation,
    HistoryTagAssociation,
    Job,
    JobParameter,
    JobToInputDatasetAssociation,
    JobToInputLibraryDatasetAssociation,
    JobToOutputDatasetAssociation,
    Library,
    LibraryDataset,
    LibraryDatasetDatasetAssociation,
    LibraryFolder,
    Page,
    PageRevision,
    StoredWorkflow,
    StoredWorkflowTagAssociation,
)
from galaxy.model.tool_shed_install import ToolVersion

log = logging.getLogger(__name__)


class ViewField:
    """
    A ViewField defines a field in a view that filter operations can be applied to
    These filter operations are either handled with standard sqlalchemy filter calls,
    or passed to specialized handlers (such as when a table join would be needed to
    do the filtering)

    Parameters:

    sqlalchemy_field - Simple filtering using existing table columns, the argument is an sqlalchemy column
        that the right hand value will be compared against

    handler - Requires more specialized code to do filtering, usually requires a table join in order to
        process the conditional

    post_filter - Unable to do simple sqlalchemy based table filtering, filter is applied to loaded object
        Thus methods avalible to the object can be used for filtering. example: a library folder must climb
        its chain of parents to find out which library it belongs to

    """

    def __init__(self, name, sqlalchemy_field=None, handler=None, post_filter=None, id_decode=False):
        self.name = name
        self.sqlalchemy_field = sqlalchemy_field
        self.handler = handler
        self.post_filter = post_filter
        self.id_decode = id_decode


class ViewQueryBaseClass:
    FIELDS: Dict[str, ViewField] = {}
    VIEW_NAME = "undefined"

    def __init__(self):
        self.query = None
        self.do_query = False
        self.state = {}
        self.post_filter = []

    def decode_query_ids(self, trans, conditional):
        if conditional.operator == "and":
            self.decode_query_ids(trans, conditional.left)
            self.decode_query_ids(trans, conditional.right)
        else:
            left_base = conditional.left.split(".")[0]
            if left_base in self.FIELDS:
                field = self.FIELDS[left_base]
                if field.id_decode:
                    conditional.right = trans.security.decode_id(conditional.right)

    def filter(self, left, operator, right):
        if operator == "and":
            self.filter(left.left, left.operator, left.right)
            self.filter(right.left, right.operator, right.right)
        else:
            left_base = left.split(".")[0]
            if left_base in self.FIELDS:
                self.do_query = True
                field = self.FIELDS[left_base]
                if field.sqlalchemy_field is not None:
                    clazz, attribute = field.sqlalchemy_field
                    sqlalchemy_field_value = getattr(clazz, attribute)
                    if operator == "=":
                        self.query = self.query.filter(sqlalchemy_field_value == right)
                    elif operator == "!=":
                        self.query = self.query.filter(sqlalchemy_field_value != right)
                    elif operator == "like":
                        self.query = self.query.filter(sqlalchemy_field_value.like(right))
                    else:
                        raise GalaxyParseError(f"Invalid comparison operator: {operator}")
                elif field.handler is not None:
                    field.handler(self, left, operator, right)
                elif field.post_filter is not None:
                    self.post_filter.append([field.post_filter, left, operator, right])
                else:
                    raise GalaxyParseError(f"Unable to filter on field: {left}")

            else:
                raise GalaxyParseError(f"Unknown field: {left}")

    def search(self, trans):
        raise GalaxyParseError(f"Unable to search view: {self.VIEW_NAME}")

    def get_results(self, force_query=False):
        if self.query is not None and (force_query or self.do_query):
            for row in self.query.distinct().all():
                selected = True
                for f in self.post_filter:
                    if not f[0](row, f[1], f[2], f[3]):
                        selected = False
                if selected:
                    yield row


##################
# Library Dataset Searching
##################


def library_extended_metadata_filter(view, left, operator, right):
    view.do_query = True
    if "extended_metadata_joined" not in view.state:
        view.query = view.query.join(ExtendedMetadata)
        view.state["extended_metadata_joined"] = True
    alias = aliased(ExtendedMetadataIndex)
    field = f"/{'/'.join(left.split('.')[1:])}"
    view.query = view.query.filter(
        and_(ExtendedMetadata.id == alias.extended_metadata_id, alias.path == field, alias.value == str(right))
    )


def ldda_parent_library_filter(item, left, operator, right):
    if operator == "=":
        return right == item.library_dataset.folder.parent_library.id
    elif operator == "!=":
        return right != item.library_dataset.folder.parent_library.id
    raise GalaxyParseError(f"Invalid comparison operator: {operator}")


class LibraryDatasetDatasetView(ViewQueryBaseClass):
    VIEW_NAME = "library_dataset_dataset"
    FIELDS = {
        "extended_metadata": ViewField("extended_metadata", handler=library_extended_metadata_filter),
        "name": ViewField("name", sqlalchemy_field=(LibraryDatasetDatasetAssociation, "name")),
        "id": ViewField("id", sqlalchemy_field=(LibraryDatasetDatasetAssociation, "id"), id_decode=True),
        "deleted": ViewField("deleted", sqlalchemy_field=(LibraryDatasetDatasetAssociation, "deleted")),
        "parent_library_id": ViewField("parent_library_id", id_decode=True, post_filter=ldda_parent_library_filter),
        "data_type": ViewField("data_type", sqlalchemy_field=(LibraryDatasetDatasetAssociation, "extension")),
    }

    def search(self, trans):
        self.query = trans.sa_session.query(LibraryDatasetDatasetAssociation)


##################
# Library Searching
##################


class LibraryView(ViewQueryBaseClass):
    VIEW_NAME = "library"
    FIELDS = {
        "name": ViewField("name", sqlalchemy_field=(Library, "name")),
        "id": ViewField("id", sqlalchemy_field=(Library, "id"), id_decode=True),
        "deleted": ViewField("deleted", sqlalchemy_field=(Library, "deleted")),
    }

    def search(self, trans):
        self.query = trans.sa_session.query(Library)


##################
# Library Folder Searching
##################
def library_folder_parent_library_id_filter(item, left, operator, right):
    if operator == "=":
        return item.parent_library.id == right
    if operator == "!=":
        return item.parent_library.id != right
    raise GalaxyParseError(f"Invalid comparison operator: {operator}")


def library_path_filter(item, left, operator, right):
    lpath = f"/{'/'.join(item.library_path)}"
    if operator == "=":
        return lpath == right
    if operator == "!=":
        return lpath != right
    raise GalaxyParseError(f"Invalid comparison operator: {operator}")


class LibraryFolderView(ViewQueryBaseClass):
    VIEW_NAME = "library_folder"
    FIELDS = {
        "name": ViewField("name", sqlalchemy_field=(LibraryFolder, "name")),
        "id": ViewField("id", sqlalchemy_field=(LibraryFolder, "id"), id_decode=True),
        "parent_id": ViewField("parent_id", sqlalchemy_field=(LibraryFolder, "parent_id"), id_decode=True),
        "parent_library_id": ViewField(
            "parent_library_id", post_filter=library_folder_parent_library_id_filter, id_decode=True
        ),
        "library_path": ViewField("library_path", post_filter=library_path_filter),
    }

    def search(self, trans):
        self.query = trans.sa_session.query(LibraryFolder)


##################
# Library Dataset Searching
##################
def library_dataset_name_filter(item, left, operator, right):
    if operator == "=":
        return item.name == right
    if operator == "!=":
        return item.name != right
    raise GalaxyParseError(f"Invalid comparison operator: {operator}")


class LibraryDatasetView(ViewQueryBaseClass):
    VIEW_NAME = "library_dataset"
    FIELDS = {
        "name": ViewField("name", post_filter=library_dataset_name_filter),
        "id": ViewField("id", sqlalchemy_field=(LibraryDataset, "id"), id_decode=True),
        "folder_id": ViewField("folder_id", sqlalchemy_field=(LibraryDataset, "folder_id"), id_decode=True),
    }

    def search(self, trans):
        self.query = trans.sa_session.query(LibraryDataset)


##################
# Tool Searching
##################
class ToolView(ViewQueryBaseClass):
    VIEW_NAME = "tool"
    FIELDS = {
        "tool_id": ViewField("name", sqlalchemy_field=(ToolVersion, "tool_id")),
        "id": ViewField("id", sqlalchemy_field=(ToolVersion, "id")),
    }

    def search(self, trans):
        self.query = trans.install_model.context.query(ToolVersion)


##################
# History Dataset Searching
##################
def history_dataset_handle_tag(view, left, operator, right):
    if operator == "=":
        view.do_query = True
        # aliasing the tag association table, so multiple links to different tags can be formed during a single query
        tag_table = aliased(HistoryDatasetAssociationTagAssociation)

        view.query = view.query.filter(HistoryDatasetAssociation.id == tag_table.history_dataset_association_id)
        tmp = right.split(":")
        view.query = view.query.filter(tag_table.user_tname == tmp[0])
        if len(tmp) > 1:
            view.query = view.query.filter(tag_table.user_value == tmp[1])
    else:
        raise GalaxyParseError(f"Invalid comparison operator: {operator}")


def history_dataset_extended_metadata_filter(view, left, operator, right):
    view.do_query = True
    if "extended_metadata_joined" not in view.state:
        view.query = view.query.join(ExtendedMetadata)
        view.state["extended_metadata_joined"] = True
    alias = aliased(ExtendedMetadataIndex)
    field = f"/{'/'.join(left.split('.')[1:])}"
    view.query = view.query.filter(
        and_(ExtendedMetadata.id == alias.extended_metadata_id, alias.path == field, alias.value == str(right))
    )


class HistoryDatasetView(ViewQueryBaseClass):
    DOMAIN = "history_dataset"
    FIELDS = {
        "name": ViewField("name", sqlalchemy_field=(HistoryDatasetAssociation, "name")),
        "id": ViewField("id", sqlalchemy_field=(HistoryDatasetAssociation, "id"), id_decode=True),
        "history_id": ViewField(
            "history_id", sqlalchemy_field=(HistoryDatasetAssociation, "history_id"), id_decode=True
        ),
        "tag": ViewField("tag", handler=history_dataset_handle_tag),
        "copied_from_ldda_id": ViewField(
            "copied_from_ldda_id",
            sqlalchemy_field=(HistoryDatasetAssociation, "copied_from_library_dataset_dataset_association_id"),
            id_decode=True,
        ),
        "copied_from_hda_id": ViewField(
            "copied_from_hda_id",
            sqlalchemy_field=(HistoryDatasetAssociation, "copied_from_history_dataset_association_id"),
            id_decode=True,
        ),
        "deleted": ViewField("deleted", sqlalchemy_field=(HistoryDatasetAssociation, "deleted")),
        "extended_metadata": ViewField("extended_metadata", handler=history_dataset_extended_metadata_filter),
    }

    def search(self, trans):
        self.query = trans.sa_session.query(HistoryDatasetAssociation)


##################
# History Searching
##################


def history_handle_tag(view, left, operator, right):
    if operator == "=":
        view.do_query = True
        tag_table = aliased(HistoryTagAssociation)
        view.query = view.query.filter(History.id == tag_table.history_id)
        tmp = right.split(":")
        view.query = view.query.filter(tag_table.user_tname == tmp[0])
        if len(tmp) > 1:
            view.query = view.query.filter(tag_table.user_value == tmp[1])
    else:
        raise GalaxyParseError(f"Invalid comparison operator: {operator}")


def history_handle_annotation(view, left, operator, right):
    if operator == "=":
        view.do_query = True
        view.query = view.query.filter(
            and_(
                HistoryAnnotationAssociation.history_id == History.id, HistoryAnnotationAssociation.annotation == right
            )
        )
    elif operator == "like":
        view.do_query = True
        view.query = view.query.filter(
            and_(
                HistoryAnnotationAssociation.history_id == History.id,
                HistoryAnnotationAssociation.annotation.like(right),
            )
        )
    else:
        raise GalaxyParseError(f"Invalid comparison operator: {operator}")


class HistoryView(ViewQueryBaseClass):
    DOMAIN = "history"
    FIELDS = {
        "name": ViewField("name", sqlalchemy_field=(History, "name")),
        "id": ViewField("id", sqlalchemy_field=(History, "id"), id_decode=True),
        "tag": ViewField("tag", handler=history_handle_tag),
        "annotation": ViewField("annotation", handler=history_handle_annotation),
        "deleted": ViewField("deleted", sqlalchemy_field=(History, "deleted")),
    }

    def search(self, trans):
        self.query = trans.sa_session.query(History)


##################
# Workflow Searching
##################


def workflow_tag_handler(view, left, operator, right):
    if operator == "=":
        view.do_query = True
        view.query = view.query.filter(StoredWorkflow.id == StoredWorkflowTagAssociation.stored_workflow_id)
        tmp = right.split(":")
        view.query = view.query.filter(StoredWorkflowTagAssociation.user_tname == tmp[0])
        if len(tmp) > 1:
            view.query = view.query.filter(StoredWorkflowTagAssociation.user_value == tmp[1])
    else:
        raise GalaxyParseError(f"Invalid comparison operator: {operator}")


class WorkflowView(ViewQueryBaseClass):
    DOMAIN = "workflow"
    FIELDS = {
        "name": ViewField("name", sqlalchemy_field=(StoredWorkflow, "name")),
        "id": ViewField("id", sqlalchemy_field=(StoredWorkflow, "id"), id_decode=True),
        "tag": ViewField("tag", handler=workflow_tag_handler),
        "deleted": ViewField("deleted", sqlalchemy_field=(StoredWorkflow, "deleted")),
    }

    def search(self, trans):
        self.query = trans.sa_session.query(StoredWorkflow)


##################
# Job Searching
##################


def job_param_filter(view, left, operator, right):
    view.do_query = True
    alias = aliased(JobParameter)
    param_name = re.sub(r"^param.", "", left)
    view.query = view.query.filter(and_(Job.id == alias.job_id, alias.name == param_name, alias.value == dumps(right)))


def job_input_hda_filter(view, left, operator, right):
    view.do_query = True
    alias = aliased(JobToInputDatasetAssociation)
    param_name = re.sub(r"^input_hda.", "", left)
    view.query = view.query.filter(and_(Job.id == alias.job_id, alias.name == param_name, alias.dataset_id == right))


def job_input_ldda_filter(view, left, operator, right):
    view.do_query = True
    alias = aliased(JobToInputLibraryDatasetAssociation)
    param_name = re.sub(r"^input_ldda.", "", left)
    view.query = view.query.filter(and_(Job.id == alias.job_id, alias.name == param_name, alias.ldda_id == right))


def job_output_hda_filter(view, left, operator, right):
    view.do_query = True
    alias = aliased(JobToOutputDatasetAssociation)
    param_name = re.sub(r"^output_hda.", "", left)
    view.query = view.query.filter(and_(Job.id == alias.job_id, alias.name == param_name, alias.dataset_id == right))


class JobView(ViewQueryBaseClass):
    DOMAIN = "job"
    FIELDS = {
        "tool_name": ViewField("tool_name", sqlalchemy_field=(Job, "tool_id")),
        "state": ViewField("state", sqlalchemy_field=(Job, "state")),
        "param": ViewField("param", handler=job_param_filter),
        "input_ldda": ViewField("input_ldda", handler=job_input_ldda_filter, id_decode=True),
        "input_hda": ViewField("input_hda", handler=job_input_hda_filter, id_decode=True),
        "output_hda": ViewField("output_hda", handler=job_output_hda_filter, id_decode=True),
    }

    def search(self, trans):
        self.query = trans.sa_session.query(Job)


##################
# Page Searching
##################


class PageView(ViewQueryBaseClass):
    DOMAIN = "page"
    FIELDS = {
        "id": ViewField("id", sqlalchemy_field=(Page, "id"), id_decode=True),
        "slug": ViewField("slug", sqlalchemy_field=(Page, "slug")),
        "title": ViewField("title", sqlalchemy_field=(Page, "title")),
        "deleted": ViewField("deleted", sqlalchemy_field=(Page, "deleted")),
    }

    def search(self, trans):
        self.query = trans.sa_session.query(Page)


##################
# Page Revision Searching
##################


class PageRevisionView(ViewQueryBaseClass):
    DOMAIN = "page_revision"
    FIELDS = {
        "id": ViewField("id", sqlalchemy_field=(PageRevision, "id"), id_decode=True),
        "title": ViewField("title", sqlalchemy_field=(PageRevision, "title")),
        "page_id": ViewField("page_id", sqlalchemy_field=(PageRevision, "page_id"), id_decode=True),
    }

    def search(self, trans):
        self.query = trans.sa_session.query(PageRevision)


# The view mapping takes a user's name for a table and maps it to a View class
# that will handle queries.

view_mapping = {
    "library": LibraryView,
    "library_folder": LibraryFolderView,
    "library_dataset_dataset": LibraryDatasetDatasetView,
    "library_dataset": LibraryDatasetView,
    "lda": LibraryDatasetView,
    "ldda": LibraryDatasetDatasetView,
    "history_dataset": HistoryDatasetView,
    "hda": HistoryDatasetView,
    "history": HistoryView,
    "workflow": WorkflowView,
    "tool": ToolView,
    "job": JobView,
    "page": PageView,
    "page_revision": PageRevisionView,
}

# The GQL gramar is defined in Parsley syntax ( https://parsley.readthedocs.io/ )

gqlGrammar = r"""
expr = 'select' bs field_desc:f bs 'from' bs word:t (
    bs 'where' bs conditional:c ws -> GalaxyQuery(f,t,c)
    | ws -> GalaxyQuery(f, t, None) )
bs = ' '+
ws = ' '*
field_desc = ( '*' -> ['*']
    | field_list )
field_list = field_name:x (
    ws ',' ws field_list:y -> [x] + y
    | -> [x]
    )
conditional = logic_statement:x (
    bs 'and' bs conditional:y -> GalaxyQueryAnd(x,y)
    | -> x
    )
word = alphanum+:x -> "".join(x)
field_name = word:x (
    '.' quote_word:y  -> x + "." + y
    |-> x
    )
alphanum = anything:x ?(re.search(r'\w', x) is not None) -> x
logic_statement = field_name:left ws comparison:comp ws value_word:right -> GalaxyQueryComparison(left, comp, right)
value_word = (
    'false' -> False
    | 'False' -> False
    | 'true' -> True
    | 'True' -> True
    | 'None' -> None
    | quote_word )
comparison = ( '=' -> '='
    | '>' -> '>'
    | '<' -> '<'
    | '!=' -> '!='
    | '>=' -> '>='
    | '<=' -> '<='
    | 'like' -> 'like'
    )
quote_word = "'" not_quote*:x "'" -> "".join(x)
not_quote = anything:x ?(x != "'") -> x
not_dquote = anything:x ?(x != '"') -> x
"""


class GalaxyQuery:
    """
    This class represents a data structure of a compiled GQL query
    """

    def __init__(self, field_list, table_name, conditional):
        self.field_list = field_list
        self.table_name = table_name
        self.conditional = conditional


class GalaxyQueryComparison:
    """
    This class represents the data structure of the comparison arguments of a
    compiled GQL query (ie where name='Untitled History')
    """

    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right


class GalaxyQueryAnd:
    """
    This class represents the data structure of the comparison arguments of a
    compiled GQL query (ie where name='Untitled History')
    """

    def __init__(self, left, right):
        self.left = left
        self.operator = "and"
        self.right = right


class GalaxyParseError(Exception):
    pass


class SearchQuery:
    def __init__(self, view, query):
        self.view = view
        self.query = query

    def decode_query_ids(self, trans):
        if self.query.conditional is not None:
            self.view.decode_query_ids(trans, self.query.conditional)

    def process(self, trans):
        self.view.search(trans)
        if self.query.conditional is not None:
            self.view.filter(self.query.conditional.left, self.query.conditional.operator, self.query.conditional.right)
        return self.view.get_results(True)

    def item_to_api_value(self, item):
        r = item.to_dict(view="element")
        if self.query.field_list.count("*"):
            return r
        o = {}
        for a in r:
            if a in self.query.field_list:
                o[a] = r[a]
        return o


class GalaxySearchEngine:
    """
    Primary class for searching. Parses GQL (Galaxy Query Language) queries and returns a 'SearchQuery' class
    """

    def __init__(self):
        self.parser = parsley.makeGrammar(
            gqlGrammar,
            {
                "re": re,
                "GalaxyQuery": GalaxyQuery,
                "GalaxyQueryComparison": GalaxyQueryComparison,
                "GalaxyQueryAnd": GalaxyQueryAnd,
            },
        )

    def query(self, query_text):
        q = self.parser(query_text).expr()

        if q.table_name in view_mapping:
            view = view_mapping[q.table_name]()
            return SearchQuery(view, q)
        raise GalaxyParseError(f"No such table {q.table_name}")
