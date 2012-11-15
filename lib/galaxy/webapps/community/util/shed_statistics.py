from time import strftime, gmtime

class ShedCounter( object ):
    def __init__( self, model ):
        # TODO: Enhance the ShedCounter to retrieve information from the db instead of displaying what's currently in memory.
        self.model = model
        self.generation_time = strftime( "%b %d, %Y", gmtime() )
        self.repositories = 0
        #self.new_repositories = 0
        self.deleted_repositories = 0
        self.invalid_tools = 0
        self.valid_tools = 0
        self.workflows = 0
        self.proprietary_datatypes = 0
        self.total_clones = 0
        self.generate_statistics()
    @property
    def sa_session( self ):
        """Returns a SQLAlchemy session"""
        return self.model.context
    def generate_statistics( self ):
        self.repositories = 0
        #self.new_repositories = 0
        self.deleted_repositories = 0
        self.invalid_tools = 0
        self.valid_tools = 0
        self.workflows = 0
        self.proprietary_datatypes = 0
        self.total_clones = 0
        for repository in self.sa_session.query( self.model.Repository ):
            self.repositories += 1
            self.total_clones += repository.times_downloaded
            is_deleted = repository.deleted
            #is_new = repository.is_new
            #if is_deleted and is_new:
            if is_deleted:
                self.deleted_repositories += 1
            #    self.new_repositories += 1
            #elif is_deleted:
            #    self.deleted_repositories += 1
            #elif is_new:
            #    self.new_repositories += 1
            else:
                processed_guids = []
                processed_invalid_tool_configs = []
                processed_relative_workflow_paths = []
                processed_datatypes = []
                # A repository's metadata_revisions are those that ignore the value of the repository_metadata.downloadable column.
                for metadata_revision in repository.metadata_revisions:
                    metadata = metadata_revision.metadata
                    if 'tools' in metadata:
                        tool_dicts = metadata[ 'tools' ]
                        for tool_dict in tool_dicts:
                            if 'guid' in tool_dict:
                                guid = tool_dict[ 'guid' ]
                                if guid not in processed_guids:
                                    self.valid_tools += 1
                                    processed_guids.append( guid )
                    if 'invalid_tools' in metadata:
                        invalid_tool_configs = metadata[ 'invalid_tools' ]
                        for invalid_tool_config in invalid_tool_configs:
                            if invalid_tool_config not in processed_invalid_tool_configs:
                                self.invalid_tools += 1
                                processed_invalid_tool_configs.append( invalid_tool_config )
                    if 'datatypes' in metadata:
                        datatypes = metadata[ 'datatypes' ]
                        for datatypes_dict in datatypes:
                            if 'extension' in datatypes_dict:
                                extension = datatypes_dict[ 'extension' ]
                                if extension not in processed_datatypes:
                                    self.proprietary_datatypes += 1
                                    processed_datatypes.append( extension )
                    if 'workflows' in metadata:
                        workflows = metadata[ 'workflows' ]
                        for workflow_tup in workflows:
                            relative_path, exported_workflow_dict = workflow_tup
                            if relative_path not in processed_relative_workflow_paths:
                                self.workflows += 1
                                processed_relative_workflow_paths.append( relative_path )
        self.generation_time = strftime( "%b %d, %Y", gmtime() )
