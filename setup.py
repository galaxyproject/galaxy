from distutils.core import setup
__revision__ = "$Rev$"

setup(
    name='Galaxy',
    version   = '2.1.%s' % __revision__.strip("$Rev: "),
    description='Galaxy Server',
    author = 'Galaxy Team',
    author_email = 'galaxy@bx.psu.edu',
    url = 'http://g2.bx.psu.edu',
     
    packages = [ 
        'galaxy', 
        'galaxy.interfaces', 
        'galaxy.tools', 
        'galaxy.tools.actions', 
        'galaxy.datatypes' 
    ],
     
)