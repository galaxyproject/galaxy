import logging, sys

class DataTransferFactory( object ):
    type = None
    config = {}
    def parse( self ):
        pass

class ScpDataTransferFactory( DataTransferFactory ):
    type = 'scp'
    def __init__( self ):
        pass
    def parse( self, config_file, elem ):
        self.config['host'] = elem.get( 'host' ) 
        self.config['user_name'] = elem.get( 'user_name' )
        self.config['password'] = elem.get( 'password' ) 
        self.config['data_location'] = elem.get( 'data_location' )
        # validate 
        for name, value in self.config.items():
            assert value, "'%s' attribute missing in 'data_transfer' element of type 'scp' in sequencer_type xml config file: '%s'." % ( name, config_file )
        
class FtpDataTransferFactory( DataTransferFactory ):
    type = 'ftp'
    def __init__( self ):
        pass
    def parse( self, elem ):
        pass
    
data_transfer_factories = dict( [ ( data_transfer.type, data_transfer() ) for data_transfer in [ ScpDataTransferFactory, FtpDataTransferFactory ] ] )

    
    



