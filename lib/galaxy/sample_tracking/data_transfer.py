import logging, sys

class DataTransferFactory( object ):
    type = None
    def parse( self ):
        pass

class ScpDataTransferFactory( DataTransferFactory ):
    type = 'scp'
    def __init__( self ):
        pass
    def parse( self, config_file, elem ):
        self.config = {}
        # TODO: The 'automatic_transfer' setting is for future use.  If set to True, we will need to 
        # ensure the sample has an associated destination data library before it moves to a certain state
        # ( e.g., Run started ).
        self.config[ 'automatic_transfer' ] = elem.get( 'automatic_transfer' )
        self.config[ 'host' ] = elem.get( 'host' ) 
        self.config[ 'user_name' ] = elem.get( 'user_name' )
        self.config[ 'password' ] = elem.get( 'password' ) 
        self.config[ 'data_location' ] = elem.get( 'data_location' )
        # 'rename_dataset' is optional and it may not be defined in all external types
        # It is only used is AB SOLiD external service type for now
        rename_dataset = elem.get( 'rename_dataset', None )
        if rename_dataset:
            self.config['rename_dataset'] = rename_dataset
        # Validate 
        for name, value in self.config.items():
            assert value, "'%s' attribute missing in 'data_transfer' element of type 'scp' in external_service_type xml config file: '%s'." % ( name, config_file )

class HttpDataTransferFactory( DataTransferFactory ):
    type = 'http'
    def __init__( self ):
        pass
    def parse( self, config_file, elem ):
        self.config = {}
        self.config[ 'automatic_transfer' ] = elem.get( 'automatic_transfer' )
        # Validate 
        for name, value in self.config.items():
            assert value, "'%s' attribute missing in 'data_transfer' element of type 'http' in external_service_type xml config file: '%s'." % ( name, config_file )

class FtpDataTransferFactory( DataTransferFactory ):
    type = 'ftp'
    def __init__( self ):
        pass
    def parse( self, elem ):
        pass

data_transfer_factories = dict( [ ( data_transfer.type, data_transfer() ) for data_transfer in [ ScpDataTransferFactory, HttpDataTransferFactory, FtpDataTransferFactory ] ] )
