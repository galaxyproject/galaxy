from galaxy.datatypes.data import Data


class LastDb(Data):
    """Class for LAST database files."""
    file_ext = 'lastdb'
    allow_datatype_change = False
    composite_type = 'basic'

    def __init__(self, **kwd):
        Data.__init__(self, **kwd)
        self.add_composite_file('lastdb.bck', is_binary=True)
        self.add_composite_file('lastdb.des', is_binary=False)  # description file
        self.add_composite_file('lastdb.prj', is_binary=False)  # project resume
        self.add_composite_file('lastdb.sds', is_binary=True)
        self.add_composite_file('lastdb.ssp', is_binary=True)
        self.add_composite_file('lastdb.suf', is_binary=True)
        self.add_composite_file('lastdb.tis', is_binary=True)
