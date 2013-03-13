"""
The GQL (Galaxy Query Language) search engine parsers a simple 'SQL-Like' query 
syntax to obtain items from the Galaxy installations.
Rather then allow/force the user to do queries on the Galaxy schema, it uses 
a small set of 'Views' which are simple table representations of complex galaxy ideas.
So while a history and it's tags may exist in seperate tables in the real schema, in 
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
import parsley
import re

from galaxy.model import HistoryDatasetAssociation, LibraryDatasetDatasetAssociation, History, Library, LibraryFolder, LibraryDataset
from galaxy.model import StoredWorkflowTagAssociation, StoredWorkflow, HistoryTagAssociation, ExtendedMetadata, ExtendedMetadataIndex
from galaxy.model import ToolVersion

from sqlalchemy import or_, and_
from sqlalchemy.orm import aliased

log = logging.getLogger( __name__ )


class ViewField(object):
    """
    A ViewField defines a field in a view that filter operations can be applied to
    These filter operations are either handled with standard sqlalchemy filter calls,
    or passed to specialized handlers (such as when a table join would be needed to 
    do the filtering)
    """
    def __init__(self, name, sqlalchemy_field=None, handler=None):
        self.name = name
        self.sqlalchemy_field = sqlalchemy_field
        self.handler = handler
        

class ViewQueryBaseClass(object):
    FIELDS = {}
    VIEW_NAME = "undefined"

    def __init__(self):
        self.query = None
        self.do_query = False
        self.state = {}

    def filter(self, left, operator, right):
        if operator == 'and':
            self.filter(left.left, left.operator, left.right)
            self.filter(right.left, right.operator, right.right)
        else:
            left_base = left.split('.')[0]
            if left_base in self.FIELDS:
                self.do_query = True
                field = self.FIELDS[left_base]
                if field.sqlalchemy_field is not None:
                    if operator == "=":
                        self.query = self.query.filter( field.sqlalchemy_field == right )
                    elif operator == "like":
                        self.query = self.query.filter( field.sqlalchemy_field.like(right) )
                    else:
                        raise GalaxyParseError("Invalid comparison operator: %s" % (operator))
                elif field.handler is not None:
                    field.handler(self, left, operator, right)
                else:
                    raise GalaxyParseError("Unable to filter on field: %s" % (left))

            else:
                raise GalaxyParseError("Unknown field: %s" % (left))

    def search(trans):
        raise GalaxyParseError("Unable to search view: %s" % (self.VIEW_NAME))

    def get_results(self, force_query=False):
        if self.query is not None and (force_query or self.do_query):
            for row in self.query.distinct().all():
                yield row


##################
#Library Dataset Searching
##################

def library_extended_metadata_filter(view, left, operator, right):
    view.do_query = True
    if 'extended_metadata_joined' not in view.state:
        view.query = view.query.join( ExtendedMetadata )
        view.state['extended_metadata_joined'] = True
    alias = aliased( ExtendedMetadataIndex )
    field = "/%s" % ("/".join(left.split(".")[1:]))
    print "FIELD", field
    view.query = view.query.filter( 
        and_( 
            ExtendedMetadata.id == alias.extended_metadata_id, 
            alias.path == field,
            alias.value == str(right) 
        )
    )


class LibraryDatasetDatasetView(ViewQueryBaseClass):
    VIEW_NAME = "library_dataset_dataset"
    FIELDS = { 
        'extended_metadata' : ViewField('extended_metadata', handler=library_extended_metadata_filter), 
        'name' : ViewField('name', sqlalchemy_field=LibraryDatasetDatasetAssociation.name ),
        'id' : ViewField('id', sqlalchemy_field=LibraryDatasetDatasetAssociation.id) 
    }

    def search(self, trans):
        self.query = trans.sa_session.query( LibraryDatasetDatasetAssociation )


##################
#Library Searching
##################

class LibraryView(ViewQueryBaseClass):
    VIEW_NAME = "library"
    FIELDS = { 
        'name' : ViewField('name', sqlalchemy_field=Library.name ),
        'id' : ViewField('id', sqlalchemy_field=Library.id) 
    }

    def search(self, trans):
        self.query = trans.sa_session.query( Library )



##################
#Library Folder Searching
##################

class LibraryFolderView(ViewQueryBaseClass):
    VIEW_NAME = "library_folder"
    FIELDS = { 
        'name' : ViewField('name', sqlalchemy_field=LibraryFolder.name ),
        'id' : ViewField('id', sqlalchemy_field=LibraryFolder.id) 
    }

    def search(self, trans):
        self.query = trans.sa_session.query( LibraryFolder )



##################
#Library Dataset Searching
##################

class LibraryDatasetView(ViewQueryBaseClass):
    VIEW_NAME = "library_dataset"
    FIELDS = { 
        'name' : ViewField('name', sqlalchemy_field=LibraryDataset.name ),
        'id' : ViewField('id', sqlalchemy_field=LibraryDataset.id) 
    }

    def search(self, trans):
        self.query = trans.sa_session.query( LibraryDataset )



##################
#Tool Searching
##################

class ToolView(ViewQueryBaseClass):
    VIEW_NAME = "tool"
    FIELDS = { 
        'tool_id' : ViewField('name', sqlalchemy_field=ToolVersion.tool_id ),
        'id' : ViewField('id', sqlalchemy_field=ToolVersion.id) 
    }

    def search(self, trans):
        self.query = trans.sa_session.query( ToolVersion )

##################
#History Dataset Searching
##################


class HistoryDatasetView(ViewQueryBaseClass):
    DOMAIN = "history_dataset"
    FIELDS = {
        'name' : ViewField('name', sqlalchemy_field=HistoryDatasetAssociation.name),
        'id' : ViewField('id',sqlalchemy_field=HistoryDatasetAssociation.id )
    }

    def search(self, trans):
        self.query = trans.sa_session.query( HistoryDatasetAssociation )


##################
#History Searching
##################


def history_handle_tag(view, left, operator, right):
    if operator == "=":
        view.do_query = True
        view.query = view.query.filter(
           History.id == HistoryTagAssociation.history_id
        )
        tmp = right.split(":")
        view.query = view.query.filter( HistoryTagAssociation.user_tname == tmp[0] )
        if len(tmp) > 1:
            view.query = view.query.filter( HistoryTagAssociation.user_value == tmp[1] )
    else:
        raise GalaxyParseError("Invalid comparison operator: %s" % (operator))


def history_handle_annotation(view, left, operator, right):
    if operator == "=":
        view.do_query = True
        view.query = view.query.filter( and_(
            HistoryAnnotationAssociation.history_id == History.id,
            HistoryAnnotationAssociation.annotation == right
            )
        )
    elif operator == "like":
        view.do_query = True
        view.query = view.query.filter( and_(
            HistoryAnnotationAssociation.history_id == History.id,
            HistoryAnnotationAssociation.annotation.like( right )
            )
        )
    else:
        raise GalaxyParseError("Invalid comparison operator: %s" % (operator))


class HistoryView(ViewQueryBaseClass):
    DOMAIN = "history"
    FIELDS = {
        'name' : ViewField('name', sqlalchemy_field=History.name),
        'id' : ViewField('id', sqlalchemy_field=History.id),
        'tag' : ViewField("tag", handler=history_handle_tag),
        'annotation' : ViewField("annotation", handler=history_handle_annotation)
    }

    def search(self, trans):
        self.query = trans.sa_session.query( History )


##################
#Workflow Searching
##################


def workflow_tag_handler(view, left, operator, right):
    if operator == "=":
        view.do_query = True
        view.query = view.query.filter(
           StoredWorkflow.id == StoredWorkflowTagAssociation.stored_workflow_id
        )
        tmp = right.split(":")
        view.query = view.query.filter( StoredWorkflowTagAssociation.user_tname == tmp[0] )
        if len(tmp) > 1:
            view.query = view.query.filter( StoredWorkflowTagAssociation.user_value == tmp[1] )
    else:
        raise GalaxyParseError("Invalid comparison operator: %s" % (operator))


class WorkflowView(ViewQueryBaseClass):
    DOMAIN = "workflow"
    FIELDS = {
        'name' : ViewField('name', sqlalchemy_field=StoredWorkflow.name),
        'id' : ViewField('id', sqlalchemy_field=StoredWorkflow.id),
        'tag' : ViewField('tag', handler=workflow_tag_handler)
    }

    def search(self, trans):
        self.query = trans.sa_session.query( StoredWorkflow )

"""
The view mapping takes a user's name for a table and maps it to a View class that will 
handle queries
"""
view_mapping = {
    'library' : LibraryView,
    'library_folder' : LibraryFolderView,
    'library_dataset_dataset' : LibraryDatasetDatasetView,
    'library_dataset' : LibraryDatasetView,
    'lda' : LibraryDatasetView,
    'ldda' : LibraryDatasetDatasetView,
    'history_dataset' : HistoryDatasetView,
    'hda' : HistoryDatasetView,
    'history' : HistoryView,
    'workflow' : WorkflowView,
    'tool' : ToolView
}

"""
The GQL gramar is defined in Parsley syntax ( http://parsley.readthedocs.org/en/latest/ )
"""

gqlGrammar = """
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
logic_statement = field_name:left ws comparison:comp ws quotable_word:right -> GalaxyQueryComparison(left, comp, right)
quotable_word = ( word | quote_word )
comparison = ( '=' -> '='
    | '>' -> '>'
    | '<' -> '<'
    | '>=' -> '>='
    | '<=' -> '<='
    | 'like' -> 'like'
    )
quote_word = "'" not_quote+:x "'" -> "".join(x)
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
        self.operator = 'and'
        self.right = right


class GalaxyParseError(Exception):
    pass

class SearchProcess:
    def __init__(self, view, query):
        self.view = view
        self.query = query
    
    def process(self, trans):
        self.view.search(trans)
        if self.query.conditional is not None:
            self.view.filter( 
                self.query.conditional.left, 
                self.query.conditional.operator,
                self.query.conditional.right )
        return self.view.get_results(True)

    def item_to_api_value(self, item):
        r = item.get_api_value( view='element' )
        if self.query.field_list.count("*"):
            return r
        o = {}
        for a in r:
            if a in self.query.field_list:
                o[a] = r[a]
        return o
                            


class GalaxySearchEngine:
    """
    Primary class for searching. Parses GQL (Galaxy Query Language) queries and returns a 'SearchProcess' class
    """
    def __init__(self):
        self.parser = parsley.makeGrammar(gqlGrammar, { 
            're' : re, 
            'GalaxyQuery' : GalaxyQuery, 
            'GalaxyQueryComparison' : GalaxyQueryComparison,
            'GalaxyQueryAnd' : GalaxyQueryAnd
        })

    def query(self, query_text):
        q = self.parser(query_text).expr()

        if q.table_name in view_mapping:
            view = view_mapping[q.table_name]()
            return SearchProcess(view, q)
        raise GalaxyParseError("No such table %s" % (q.table_name))

