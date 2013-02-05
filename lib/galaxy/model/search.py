"""
Classes for implmenting search methods for various data models
"""

import logging
from galaxy.model.orm import *
from galaxy.model import *

from sqlalchemy import or_, and_

log = logging.getLogger( __name__ )


"""

The search model is a simplified view of the SQL schema. A search domain 
typicaly covers a base data table, but it's fields can be constructs of multiple 
tables that are joined togeather. For example, a History dataset may have tags associated with it.
The Search class simplifies the joining process between the history dataset and the tags table, 
and presents the 'tag' field as a single concept that can be filtered against.


"""

class SearchField(object):

    def __init__(self, name):
        self.name = name
        self.other = None
        self.mode = None

    def __eq__(self, other ):
        self.other = other
        self.mode = "=="
        return self

    def like(self, other):
        self.other = other
        self.mode = "like"
        return self

class QueryBaseClass(object):
    OUTPUT_COLUMNS = []

    def __init__(self, base_query):
        self.query = base_query
        self.do_query = False

    def get_results(self, force_query=False):
        if self.query is not None and (force_query or self.do_query):
            for row in self.query.distinct().all():
                yield row


class SearchBaseClass(object):

    def get_field(self, name):
        for f_obj in self.FIELDS:
            if isinstance(f_obj, SearchField):
                if f_obj.name == name:
                    return f_obj
            else:
                print "Not SearchField", f_obj
        return None

    @staticmethod
    def search(trans):
        return None


##################
#Library Searching
##################

class LibraryDatasetQuery(QueryBaseClass):
    DOMAIN = "library_dataset"
    OUTPUT_COLUMNS = [ 'extended_metadata', 'name', 'id' ]
    def filter(self, arg):
        print "Library", arg
        if arg.name == 'extended_metadata':
            self.do_query = True
            self.query = self.query.join( ExtendedMetadata )
            ex_meta = arg.other
            for f in ex_meta:
                alias = aliased( ExtendedMetadataIndex )
                self.query = self.query.filter( 
                    and_( 
                        ExtendedMetadata.id == alias.extended_metadata_id, 
                        alias.path == "/" + f,
                        alias.value == str(ex_meta[f]) 
                    )
                )
        if arg.name == "name":
            self.do_query = True
            if arg.mode == "==":
                self.query = self.query.filter( LibraryDatasetDatasetAssociation.name == arg.other )
            if arg.mode == "like":
                self.query = self.query.filter( LibraryDatasetDatasetAssociation.name.like(arg.other) )



class LibraryDatasetSearch(SearchBaseClass):
    FIELDS = [
        SearchField("name"),
        SearchField("id"),
        SearchField("extended_metadata")
    ]

    @staticmethod
    def search(trans):
        query = trans.sa_session.query( LibraryDatasetDatasetAssociation )
        return LibraryDatasetQuery(query)

##################
#History Dataset Searching
##################


class HistoryDatasetQuery(QueryBaseClass):
    DOMAIN = "history_dataset"
    OUTPUT_COLUMNS = ['name', 'id']

    def filter(self, arg):
        if arg.name == 'name':
            if arg.mode == "==":
                self.do_query = True
                self.query= self.query.filter( HistoryDatasetAssociation.name == arg.other )
            if arg.mode == "like":
                self.do_query = True
                self.query= self.query.filter( HistoryDatasetAssociation.name.like(arg.other) )

class HistoryDatasetSearch(SearchBaseClass):
    FIELDS = [
        SearchField("name")
    ]
    @staticmethod
    def search(trans):
        query = trans.sa_session.query( HistoryDatasetAssociation )
        return HistoryDatasetQuery(query)


##################
#History Searching
##################


class HistoryQuery(QueryBaseClass):
    DOMAIN = "history"
    OUTPUT_COLUMNS = ['name', 'id']

    def filter(self, arg):
        if arg.name == 'name':
            if arg.mode == "==":
                self.do_query = True
                self.query = self.query.filter( History.name == arg.other )
            if arg.mode == "like":
                self.do_query = True
                self.query = self.query.filter( History.name.like(arg.other) )

        if arg.name == 'tag':
            self.do_query = True
            self.query = self.query.filter(
               History.id == HistoryTagAssociation.history_id
            )
            tmp = arg.other.split(":")
            self.query = self.query.filter( HistoryTagAssociation.user_tname == tmp[0] )
            if len(tmp) > 1:
                self.query = self.query.filter( HistoryTagAssociation.user_value == tmp[1] )

        if arg.name == 'annotation':
            if arg.mode == "==":
                self.do_query = True
                self.query = self.query.filter( and_(
                    HistoryAnnotationAssociation.history_id == History.id,
                    HistoryAnnotationAssociation.annotation == arg.other
                    )
                )

            if arg.mode == "like":
                self.do_query = True
                self.query = self.query.filter( and_(
                    HistoryAnnotationAssociation.history_id == History.id,
                    HistoryAnnotationAssociation.annotation.like( arg.other )
                    )
                )


class HistorySearch(SearchBaseClass):
    FIELDS = [
        SearchField("name"),
        SearchField("tag"),
        SearchField("annotation")
    ]

    @staticmethod
    def search(trans):
        query = trans.sa_session.query( History )
        return HistoryQuery(query)

##################
#Workflow Searching
##################



class WorkflowQuery(QueryBaseClass):
    DOMAIN = "workflow"
    OUTPUT_COLUMNS = ['name', 'id']

    def filter(self, arg):
        if arg.name == 'name':
            self.do_query = True
            self.query = self.query.filter( StoredWorkflow.name == arg.other )
        if arg.name == 'tag':
            self.do_query = True
            self.query = self.query.filter( and_(
                Tag.name == arg.other, 
                Tag.id == StoredWorkflowTagAssociation.tag_id, 
                StoredWorkflowTagAssociation.stored_workflow_id == StoredWorkflow.id )
            )
            self.query = self.query.filter(
               Workflow.id == StoredWorkflowTagAssociation.workflow_id
            )
            tmp = arg.other.split(":")
            self.query = self.query.filter( StoredWorkflowTagAssociation.user_tname == tmp[0] )
            if len(tmp) > 1:
                self.query = self.query.filter( StoredWorkflowTagAssociation.user_value == tmp[1] )

        
class WorkflowSearch(SearchBaseClass):

    FIELDS = [
        SearchField("name"),
        SearchField("tag")
    ]

    @staticmethod
    def search(trans):
        query = trans.sa_session.query( StoredWorkflow )
        return WorkflowQuery(query)


search_mapping = {
    'library_dataset' : LibraryDatasetSearch,
    'history_dataset' : HistoryDatasetSearch,
    'history' : HistorySearch,
    'workflow' : WorkflowSearch
}


