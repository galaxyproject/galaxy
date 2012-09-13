#!/usr/bin/env python

# Script requires handlebars compiler be installed; use node package manager 
# to install handlebars.

"""%prog [options] [ specific .handlebars or .html template file to compile ]
    Compiles handlebars templates into javascript for better load times and performance.
   
    Handlebars compilation errors will print to stderr.
    NOTE!: you will need node.js, npm, and handlebars (installed from npm) in order to compile templates
        See http://handlebarsjs.com/precompilation.html for more info.
    
    Should be called from the $GLX_ROOT/static/scripts/templates directory.   
    Compiled templates will be written to the compiled/ directory.
    
    If the --multi-ext option is passed a file extension string, the script will:
        * search for *.<extension> in the current directory,
        * extract each '<script type="text/template"> from the file and write them into a new handlebars file
            named using the id of the script tag (eg. id="undeleteMsg" -> undeleteMsg.handlebars)
        * these new handlebars scripts will be compiled along with any other handlebars templates in the dir
        
    additionally for each of those files, the script will:
        * extract each '<script type="text/javascript"> from the file and write them ALL into a single js file
            named using the prefix 'helpers-' and the basename of the enclosing file
            (eg. common-templates.html -> helpers-common-templates.js )
        * these new handlebars scripts will be compiled along with any other handlebars templates in the dir
            These files can be included as if they were templates (eg. h.templates( 'helpers-common-templates' ) )
            
    This hopefully will allow both multiple templates and their associated Handlebars helper functions to be
        included in one file.
        
    Currently, this works (best?) if:
        * the multiple templates are within one html file
        * each template is enclosed in a <script> tag with type="text/template" and some id attribute
        * each helper fn is enclosed in a <script> tag with type="text/javascript" and some id attribute
    e.g. <script type="text/template" id="history-deletedMsg" class="template">Deleted {{ msg }}</script>
    
"""
# ------------------------------------------------------------------------------

TODO = """
remove intermediate, handlebars step of multi->handlebars->compiled/.js (if handlebars does stdin)
"""

import sys

from glob import glob
from subprocess import call
from shutil import copyfile
from os import path
from optparse import OptionParser
from HTMLParser import HTMLParser

import logging
log = logging.getLogger( __name__ )

COMPILED_DIR = 'compiled'
COMPILED_EXT = '.js'
COMPILE_CMD_STR = "handlebars %s -f %s"
COMPILE_MINIMIZE_SWITCH = ' -m'

# both of these are off by default for backward compat
DEFAULT_MINIMIZATION = False
DEFAULT_MULTI_EXT = None #'.html'

# ------------------------------------------------------------------------------
class HTMLMultiTemplateParser( HTMLParser ):
    """Parses multiple templates from an HTML file, saving them to a map of:
        { id : template_text, ... }
        
    Templates must:
        * be within the TEMPLATE_TAG
        * TEMPLATE_TAG must have a type attribute
        * that attr must == TEMPLATE_TYPE
        * TEMPLATE_TAG cannot be nested within one another
        * TEMPLATE_TAG must have an id attribute
    """
    TEMPLATE_TAG = 'script'
    TEMPLATE_TYPES = [ 'text/template' ]
    
    HELPER_TAG = 'script'
    HELPER_TYPES = [ 'text/javascript' ]
    
    def __init__( self ):
        HTMLParser.__init__( self )
        self.templates = {}
        self.curr_template_id = None
        self.template_data = ''
    
        self.helpers = {}
        self.curr_helper_id = None
        self.helper_data = ''
    
    def is_template_tag( self, tag, attr_dict ):
        # both tag and type attr must match
        return ( ( tag == self.TEMPLATE_TAG )
             and ( 'type' in attr_dict )
             and ( attr_dict[ 'type' ] in self.TEMPLATE_TYPES ) )
    
    def is_helper_tag( self, tag, attr_dict ):
        # both tag and type attr must match
        return ( ( tag == self.HELPER_TAG )
             and ( 'type' in attr_dict )
             and ( attr_dict[ 'type' ] in self.HELPER_TYPES ) )
    
    def handle_starttag( self, tag, attrs ):
        attr_dict = dict( attrs )
        if self.is_template_tag( tag, attr_dict ):
            log.debug( "\t template tag: %s, %s", tag, str( attr_dict ) );
            
            # as far as I know these tags can't/shouldn't nest/overlap
            #pre: not already inside a template/helper tag
            assert self.curr_template_id == None, "Found nested template tag: %s" % ( self.curr_template_id )
            assert self.curr_helper_id   == None, "Found template tag inside helper: %s" % ( self.curr_helper_id )
            #pre: must have an id
            assert 'id' in attr_dict, "No id attribute in template: " + str( attr_dict )
            
            self.curr_template_id = attr_dict[ 'id' ]
            
        elif self.is_helper_tag( tag, attr_dict ):
            log.debug( "\t helper tag: %s, %s", tag, str( attr_dict ) );
            
            #pre: not already inside a template/helper tag
            assert self.curr_helper_id   == None, "Found nested helper tag: %s" % ( self.curr_helper_id )
            assert self.curr_template_id == None, "Found helper tag inside template: %s" % ( self.curr_template_id )
            #pre: must have an id
            assert 'id' in attr_dict, "No id attribute in helper: " + str( attr_dict )
            
            self.curr_helper_id = attr_dict[ 'id' ]
        
    def handle_endtag( self, tag ):
        if( ( tag == self.TEMPLATE_TAG )
        and ( self.curr_template_id ) ):
            log.debug( "\t ending template tag :", tag, self.curr_template_id );
            
            # store the template data by the id
            if self.template_data:
                self.templates[ self.curr_template_id ] = self.template_data
                
            #! reset for next template
            self.curr_template_id = None
            self.template_data = ''
            
        elif( ( tag == self.HELPER_TAG )
        and   ( self.curr_helper_id ) ):
            log.debug( "\t ending helper tag :", tag, self.curr_template_id );
            
            # store the template data by the id
            if self.helper_data:
                self.helpers[ self.curr_helper_id ] = self.helper_data
                
            #! reset for next template
            self.curr_helper_id = None
            self.helper_data = ''
        
    def handle_data(self, data):
        data = data.strip()
        if data:
            if self.curr_template_id:
                log.debug( "\t template text :", data );
                self.template_data += data

            elif self.curr_helper_id:
                log.debug( "\t helper js fn :", data );
                self.helper_data += data


# ------------------------------------------------------------------------------
def break_multi_template( multi_template_filename ):
    """parse the multi template, writing each template into a new handlebars tmpl and returning their names"""
    template_filenames = []
    parser = HTMLMultiTemplateParser()
    
    # parse the multi template
    print "\nBreaking multi-template file %s into individual templates and helpers:" % ( multi_template_filename )
    with open( multi_template_filename, 'r' ) as multi_template_file:
        # wish I could use a gen here
        parser.feed( multi_template_file.read() )
        
        # after breaking, write each indiv. template and save the names
        for template_id, template_text in parser.templates.items():
            handlebar_template_filename = template_id + '.handlebars'
            with open( handlebar_template_filename, 'w' ) as handlebar_template_file:
                handlebar_template_file.write( template_text )
                
            template_filenames.append( handlebar_template_filename )
            
        # write all helpers to a 'helper-' prefixed js file in the compilation dir
        if parser.helpers:
            helper_filename = 'helpers-' + path.splitext( multi_template_filename )[0] + '.js'
            helper_filename = path.join( COMPILED_DIR, helper_filename )
            with open( helper_filename, 'w' ) as helper_file:
                for helper_fn_name, helper_fn in parser.helpers.items():
                    print '(helper)', helper_fn_name
                    helper_file.write( helper_fn + '\n' )
            
    print '\n'.join( template_filenames )
    return template_filenames


# ------------------------------------------------------------------------------
def compile_template( template_filename, minimize=False ):
    """compile the given template file (optionally minimizing the js) using subprocess.
    
    Use the basename of the template file for the outputed js.
    """
    template_basename = path.splitext( path.split( template_filename )[1] )[0]
    compiled_filename = path.join( COMPILED_DIR, template_basename + COMPILED_EXT )
    
    command_string = COMPILE_CMD_STR % ( template_filename, compiled_filename )
    if minimize:
        command_string += COMPILE_MINIMIZE_SWITCH
    print command_string
    return call( command_string, shell=True )


# ------------------------------------------------------------------------------
def main( options, args ):
    """Break multi template files into single templates, compile all single templates.
    
    If args, compile that as a list of specific handlebars and/or multi template files.
    """
    print "(Call this script with the '-h' option for more help)"
    
    handlebars_templates = []
    # If specific scripts specified on command line, just compile them,
    if len( args ) >= 1:
        handlebars_templates = filter( lambda( x ): x.endswith( '.handlebars' ), args )
        
    # otherwise compile all in the current dir
    else:
        handlebars_templates = glob( '*.handlebars' )

    # if desired, break up any passed-in or found multi template files
    #   adding the names of the new single templates to those needing compilation
    if options.multi_ext:
        multi_templates = []
        if len( args ) >= 1:
            multi_templates = filter( lambda( x ): x.endswith( options.multi_ext ), args )
        else:
            multi_templates = glob( '*' + options.multi_ext )
            
        for multi_template_filename in multi_templates:
            handlebars_templates.extend( break_multi_template( multi_template_filename ) )
            
    # unique filenames only (Q&D)
    handlebars_templates = list( set( handlebars_templates ) )
        
    # compile the templates
    print "\nCompiling templates:"
    filenames_w_possible_errors = []
    for handlebars_template in handlebars_templates:
        shell_ret = compile_template( handlebars_template, options.minimize )
        if shell_ret:
            filenames_w_possible_errors.append( handlebars_template )
    
    # report any possible errors
    if filenames_w_possible_errors:
        print "\nThere may have been errors on the following files:"
        print ',\n'.join( filenames_w_possible_errors )
        print "\nCall this script with the '-h' for more help"


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    optparser = OptionParser( usage=__doc__ )
    optparser.add_option( '-m', '--minimize', dest='minimize', action='store_true', default=DEFAULT_MINIMIZATION,
                          help=( 'minimize compiled template scripts via handlebars '
                              + '(defaults to %s)' % DEFAULT_MINIMIZATION ) )
    optparser.add_option( '--multi-ext', dest='multi_ext', metavar="FILE_EXTENSION", default=DEFAULT_MULTI_EXT,
                          help=( 'indicates that files ending with the given string contain multiple '
                               + 'templates and the script should break those into individual '
                               + 'handlebars templates (defaults to "%s")' ) % DEFAULT_MULTI_EXT )
    
    ( options, args ) = optparser.parse_args()    
    sys.exit( main( options, args ) )
    
