#!/usr/bin/env python

"""
CSS processor for Galaxy style sheets. Supports the following features:

- Nested rule definition
- Mixins
- Variable substitution in values

"""

import sys, string, os.path, os

new_path = [ os.path.join( os.getcwd(), '..', '..', '..', "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
import pkg_resources
from galaxy.util.odict import odict

from pyparsing import *
#from odict import odict

try:
    import Image
except ImportError:
    from PIL import Image

def cross_lists(*sets):
    """
    Return the cross product of the arguments
    """
    wheels = map(iter, sets) 
    digits = [it.next() for it in wheels]
    while True:
        yield digits[:]
        for i in range(len(digits)-1, -1, -1):
            try:
                digits[i] = wheels[i].next()
                break
            except StopIteration:
                wheels[i] = iter(sets[i])
                digits[i] = wheels[i].next()
        else:
            break
        
def find_file( path, fname ):
    # Path can be a single directory or a ':' separated list
    if ':' in path:
        paths = path.split( ':' )
    else:
        paths = [ path ]
    # Check in each directory
    for path in paths:
        fullname = os.path.join( path, fname )
        if os.path.exists( fullname ):
            return fullname
    # Not found
    raise IOError( "File '%s' not found in path '%s'" % ( fname, paths ) )

def build_stylesheet_parser():
    """
    Returns a PyParsing parser object for CSS
    """

    # Forward declerations for recursion
    rule = Forward()
    
    # Structural syntax, supressed from parser output
    lbrace = Literal("{").suppress()
    rbrace = Literal("}").suppress()
    colon  = Literal(":").suppress()
    semi   = Literal(";").suppress()
    
    ident = Word( alphas + "_", alphanums + "_-" ) 
    
    # Properties
    prop_name  = Word( alphas + "_-*", alphanums + "_-" ) 
    prop_value  = CharsNotIn( ";" )  # expand this as needed
    property_def = Group( prop_name + colon + prop_value + semi ).setResultsName( "property_def" )
    
    # Selectors
    #   Just match anything that looks like a selector, including element, class,
    #   id, attribute, and pseudoclass. Attributes are not handled properly (spaces,
    #   and even newlines in the quoted string are legal).
    simple_selector = Word( alphanums + "@.#*:()[]|=\"'_-" )
    combinator = Literal( ">" ) | Literal( "+" )
    selector = Group( simple_selector + ZeroOrMore( Optional( combinator ) + simple_selector ) )
    selectors = Group( delimitedList( selector ) )
    
    selector_mixin = Group( selector + semi ).setResultsName( "selector_mixin" )
    
    # Rules
    rule << Group( selectors +
                   lbrace +
                   Group( ZeroOrMore( property_def | rule | selector_mixin ) ) + 
                   rbrace ).setResultsName( "rule" )
    
    # A whole stylesheet
    stylesheet = ZeroOrMore( rule )
    
    # C-style comments should be ignored, as should "##" comments
    stylesheet.ignore( cStyleComment )
    stylesheet.ignore( "##" + restOfLine )
    
    return stylesheet

stylesheet_parser = build_stylesheet_parser()

class LessTemplate( string.Template ):
    delimeter = "@"

class CSSProcessor( object ):
    
    def process( self, file, out, variables, image_dir, out_dir ):
        # Build parse tree
        results = stylesheet_parser.parseFile( sys.stdin, parseAll=True )
        # Expand rules (elimimate recursion and resolve mixins)
        rules = self.expand_rules( results )
        # Expand variables (inplace)
        self.expand_variables( rules, variables )
        # Do sprites
        self.make_sprites( rules, image_dir, out_dir )
        # Print
        self.print_rules( rules, out )
        
    def expand_rules( self, parse_results ):
        mixins = {}
        rules = []
        # Visitor for recursively expanding rules
        def visitor( r, selector_prefixes ):
            # Concatenate combinations and build list of expanded selectors
            selectors = [ " ".join( s ) for s in r[0] ]
            full_selector_list = selector_prefixes + [selectors] 
            full_selectors = []
            for l in cross_lists( *full_selector_list ):
                full_selectors.append(  " ".join( l ) )
            # Separate properties from recursively defined rules
            properties = []
            children = []
            for dec in r[1]:
                type = dec.getName()
                if type == "property_def":
                    properties.append( dec )
                elif type == "selector_mixin":
                    properties.extend( mixins[dec[0][0]] )
                else:
                    children.append( dec )
            rules.append( ( full_selectors, properties ) )
            # Save by name for mixins (not smart enough to combine rules!)        
            for s in full_selectors:
                mixins[ s ] = properties;
            # Visit children
            for child in children:
                visitor( child, full_selector_list )
        # Call at top level
        for p in parse_results:
            visitor( p, [] )
        # Return the list of expanded rules
        return rules
            
    def expand_variables( self, rules, context ):
        for selectors, properties in rules:
            for p in properties:
                p[1] = string.Template( p[1] ).substitute( context ).strip()
                # Less style uses @ to prefix variables
                p[1] = LessTemplate( p[1] ).substitute( context ).strip()
    
    def make_sprites( self, rules, image_dir, out_dir ):
        
        pad = 10
        
        class SpriteGroup( object ):
            def __init__( self, name ):
                self.name = name
                self.offset = 0
                self.sprites = odict()
            def add_or_get_sprite( self, fname ):
                if fname in self.sprites:
                    return self.sprites[fname]
                else:
                    sprite = self.sprites[fname] = Sprite( fname, self.offset )
                    self.offset += sprite.image.size[1] + pad
                    return sprite
        
        class Sprite( object ):
            def __init__( self, fname, offset ):
                self.fname = fname
                self.image = Image.open( find_file( image_dir, fname ) )
                self.offset = offset
                
        sprite_groups = {}
        
        for i in range( len( rules ) ):
            properties = rules[i][1]
            new_properties = []
            # Find sprite properties (and remove them). Last takes precedence
            sprite_group_name = None
            sprite_filename = None
            sprite_horiz_position = "0px"
            for name, value in properties:
                if name == "-sprite-group":
                    sprite_group_name = value
                elif name == "-sprite-image":
                    sprite_filename = value
                elif name == "-sprite-horiz-position":
                    sprite_horiz_position = value
                else:
                    new_properties.append( ( name, value ) )
            # If a sprite filename was found, deal with it... 
            if sprite_group_name and sprite_filename:
                if sprite_group_name not in sprite_groups:
                    sprite_groups[sprite_group_name] = SpriteGroup( sprite_group_name )
                sprite_group = sprite_groups[sprite_group_name]
                sprite = sprite_group.add_or_get_sprite( sprite_filename )
                new_properties.append( ( "background", "url(%s.png) no-repeat %s -%dpx" % ( sprite_group.name, sprite_horiz_position, sprite.offset ) ) )
            # Save changed properties
            rules[i] = ( rules[i][0], new_properties )
        
        # Generate new images
        for group in sprite_groups.itervalues():
            w = 0
            h = 0
            for sprite in group.sprites.itervalues():
                sw, sh = sprite.image.size
                w = max( w, sw )
                h += sh + pad
            master = Image.new( mode='RGBA', size=(w, h), color=(0,0,0,0) )
            offset = 0
            for sprite in group.sprites.itervalues():
                master.paste( sprite.image, (0,offset) )
                offset += sprite.image.size[1] + pad
            master.save( os.path.join( out_dir, group.name + ".png" ) )
            
    def print_rules( self, rules, file ):
        for selectors, properties in rules:
            file.write( ",".join( selectors ) )
            file.write( "{" )
            for name, value in properties:
                file.write( "%s:%s;" % ( name, value ) )
            file.write( "}\n" )

def main():

    # Read variable definitions from a (sorta) ini file
    context = dict()
    for line in open( sys.argv[1] ):
        if line.startswith( '#' ):
            continue
        key, value = line.rstrip("\r\n").split( '=' )
        if value.startswith( '"' ) and value.endswith( '"' ):
            value = value[1:-1]
        context[key] = value
        
    image_dir = sys.argv[2]
    out_dir = sys.argv[3]

    try:
        
        processor = CSSProcessor()
        processor.process( sys.stdin, sys.stdout, context, image_dir, out_dir )
        
    except ParseException, e:
        
        print >> sys.stderr, "Error:", e
        print >> sys.stderr, e.markInputline()
        sys.exit( 1 )
    

if __name__ == "__main__":
    main()
