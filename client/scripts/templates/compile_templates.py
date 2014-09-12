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
import os
from optparse import OptionParser
import re

import logging as log
log.basicConfig(
    #level = log.DEBUG,
    name = __name__
)

COMPILED_DIR = 'compiled'
COMPILED_EXT = '.js'
COMPILE_CMD_STR = "handlebars %s -f %s"
COMPILE_MINIMIZE_SWITCH = ' -m'

TEMPLATE_TAG = 'script'
TEMPLATE_TYPE = 'text/template'
HELPER_TYPE = 'text/javascript'

# both of these are off by default for backward compat
DEFAULT_MINIMIZATION = False
DEFAULT_MULTI_EXT = None #'.html'

# ------------------------------------------------------------------------------
def parse_html_tag_attrs( string ):
    attrs = {}
    for match in re.finditer( r'(?P<key>\w+?)=[\'|\"](?P<val>.*?)[\'|\"]', string, re.DOTALL | re.MULTILINE ):
        match = match.groupdict()
        key = match[ 'key' ]
        val = match[ 'val' ]
        attrs[ key ] = val
    return attrs

def split_on_html_tag( string, tag ):
    tag_pattern = r'<%s\s*(?P<attrs>.*?)>(?P<body>.*?)</%s>' % ( tag, tag )
    log.debug( tag_pattern )
    tag_pattern = re.compile( tag_pattern, re.MULTILINE | re.DOTALL )
    
    found_list = re.findall( tag_pattern, string )
    for attrs, body in found_list:
        yield ( parse_html_tag_attrs( attrs ), body )

def filter_on_tag_type( generator, type_attr_to_match ):
    for attrs, body in generator:
        log.debug( 'attrs: %s', str( attrs ) )
        if( ( 'type' in attrs )
        and ( attrs[ 'type' ] == type_attr_to_match ) ):
            yield attrs, body

        
# ------------------------------------------------------------------------------
def break_multi_template( multi_template_filename ):
    """parse the multi template, writing each template into a new handlebars tmpl and returning their names"""
    template_filenames = []
    
    # parse the multi template
    print "\nBreaking multi-template file %s into individual templates and helpers:" % ( multi_template_filename )
    with open( multi_template_filename, 'r' ) as multi_template_file:
        multi_template_file_text = multi_template_file.read()
        
        # write a template file for each template (name based on id in tag)
        tag_generator = split_on_html_tag( multi_template_file_text, TEMPLATE_TAG )
        for attrs, template_text in filter_on_tag_type( tag_generator, TEMPLATE_TYPE ):
            if( 'id' not in attrs ):
                log.warning( 'Template has no "id". attrs: %s' %( str( attrs ) ) )
                continue
            
            template_id = attrs[ 'id' ]
            template_text = template_text.strip()
            handlebar_template_filename = template_id + '.handlebars'
            with open( handlebar_template_filename, 'w' ) as handlebar_template_file:
                handlebar_template_file.write( template_text )
                
            log.debug( "%s\n%s\n", template_id, template_text )
            template_filenames.append( handlebar_template_filename )
            
        ## write all helpers to a single 'helper-' prefixed js file in the compilation dir
        helper_fns = []
        # same tag, different type
        tag_generator = split_on_html_tag( multi_template_file_text, TEMPLATE_TAG )
        for attrs, helper_text in filter_on_tag_type( tag_generator, HELPER_TYPE ):
            helper_text = helper_text.strip()
            print '(helper):', ( attrs[ 'id' ] if 'id' in attrs else '(No id)' )
            
            helper_fns.append( helper_text )

        if helper_fns:
            # prefix original filename (in compiled dir) and write all helper funcs to that file
            helper_filename = 'helpers-' + os.path.splitext( multi_template_filename )[0] + '.js'
            helper_filename = os.path.join( COMPILED_DIR, helper_filename )
            with open( helper_filename, 'w' ) as helper_file:
                helper_file.write( '\n'.join( helper_fns ) )
            print '(helper functions written to %s)' % helper_filename
            
    print '\n'.join( template_filenames )
    return template_filenames


# ------------------------------------------------------------------------------
def compile_template( template_filename, minimize=False ):
    """compile the given template file (optionally minimizing the js) using subprocess.
    
    Use the basename of the template file for the outputed js.
    """
    template_basename = os.path.splitext( os.path.split( template_filename )[1] )[0]
    compiled_filename = os.path.join( COMPILED_DIR, template_basename + COMPILED_EXT )
    
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
    multi_template_template_filenames = []
    if options.multi_ext:
        multi_templates = []
        if len( args ) >= 1:
            multi_templates = filter( lambda( x ): x.endswith( options.multi_ext ), args )
        else:
            multi_templates = glob( '*' + options.multi_ext )
            
        for multi_template_filename in multi_templates:
            multi_template_template_filenames.extend( break_multi_template( multi_template_filename ) )
            
    # unique filenames only (Q&D)
    handlebars_templates = list( set( handlebars_templates + multi_template_template_filenames ) )
        
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

    # delete multi template intermediate files
    if options.remove_intermediate:
        print "\nCleaning up intermediate multi-template template files:"
        for filename in multi_template_template_filenames:
            try:
                print 'removing', filename
                os.remove( filename )
            except Exception, exc:
                print exc


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
    optparser.add_option( '--no-remove', action='store_false', dest='remove_intermediate', default=True,
                          help=( 'remove intermediate *.handlebars files when using multiple template'
                               + 'files (defaults to "True")' ) )

    ( options, args ) = optparser.parse_args()
    sys.exit( main( options, args ) )
    
