from galaxy import eggs

eggs.require( "SVGFig" )
import svgfig


class WorkflowCanvas( object ):

    def __init__( self ):
        self.canvas = svgfig.canvas( style="stroke:black; fill:none; stroke-width:1px; stroke-linejoin:round; text-anchor:left" )
        self.text = svgfig.SVG( "g" )
        self.connectors = svgfig.SVG( "g" )
        self.boxes = svgfig.SVG( "g" )

        svgfig.Text.defaults[ "font-size" ] = "10px"

    def finish( self, max_x, max_width, max_y ):
        canvas = self.canvas
        canvas.append( self.connectors )
        canvas.append( self.boxes )
        canvas.append( self.text )
        width, height = ( max_x + max_width + 50 ), max_y + 300
        canvas[ 'width' ] = "%s px" % width
        canvas[ 'height' ] = "%s px" % height
        canvas[ 'viewBox' ] = "0 0 %s %s" % ( width, height )
