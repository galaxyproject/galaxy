from galaxy import eggs

eggs.require( "SVGFig" )
import svgfig

MARGIN = 5
LINE_SPACING = 15


class WorkflowCanvas( object ):

    def __init__( self ):
        self.canvas = svgfig.canvas( style="stroke:black; fill:none; stroke-width:1px; stroke-linejoin:round; text-anchor:left" )
        self.text = svgfig.SVG( "g" )
        self.connectors = svgfig.SVG( "g" )
        self.boxes = svgfig.SVG( "g" )

        svgfig.Text.defaults[ "font-size" ] = "10px"

        self.in_pos = {}
        self.out_pos = {}
        self.widths = {}
        self.max_x = 0
        self.max_y = 0
        self.max_width = 0

    def finish( self, max_x, max_width, max_y ):
        canvas = self.canvas
        canvas.append( self.connectors )
        canvas.append( self.boxes )
        canvas.append( self.text )
        width, height = ( max_x + max_width + 50 ), max_y + 300
        canvas[ 'width' ] = "%s px" % width
        canvas[ 'height' ] = "%s px" % height
        canvas[ 'viewBox' ] = "0 0 %s %s" % ( width, height )

    def add_boxes( self, step_dict, width, name_fill ):
        margin = MARGIN
        line_px = LINE_SPACING

        x, y = step_dict[ 'position' ][ 'left' ], step_dict[ 'position' ][ 'top' ]
        self.boxes.append( svgfig.Rect( x - margin, y, x + width - margin, y + 30, fill=name_fill ).SVG() )
        box_height = ( len( step_dict[ 'data_inputs' ] ) + len( step_dict[ 'data_outputs' ] ) ) * line_px + margin
        # Draw separator line.
        if len( step_dict[ 'data_inputs' ] ) > 0:
            box_height += 15
            sep_y = y + len( step_dict[ 'data_inputs' ] ) * line_px + 40
            self.text.append( svgfig.Line( x - margin, sep_y, x + width - margin, sep_y ).SVG() )
        # Define an input/output box.
        self.boxes.append( svgfig.Rect( x - margin, y + 30, x + width - margin, y + 30 + box_height, fill="#ffffff" ).SVG() )

    def add_text( self, module_data_inputs, module_data_outputs, step, module_name ):
        left, top = step.position[ 'left' ], step.position[ 'top' ]
        x, y = left, top
        order_index = step.order_index
        max_len = len( module_name ) * 1.5
        self.text.append( svgfig.Text( x, y + 20, module_name, **{ "font-size": "14px" } ).SVG() )

        y += 45

        count = 0
        line_px = LINE_SPACING
        in_pos = self.in_pos
        out_pos = self.out_pos

        for di in module_data_inputs:
            cur_y = y + count * line_px
            if order_index not in in_pos:
                in_pos[ order_index ] = {}
            in_pos[ order_index ][ di[ 'name' ] ] = ( x, cur_y )
            self.text.append( svgfig.Text( x, cur_y, di[ 'label' ] ).SVG() )
            count += 1
            max_len = max( max_len, len( di[ 'label' ] ) )
        if len( module_data_inputs ) > 0:
            y += 15
        for do in module_data_outputs:
            cur_y = y + count * line_px
            if order_index not in out_pos:
                out_pos[ order_index ] = {}
            out_pos[ order_index ][ do[ 'name' ] ] = ( x, cur_y )
            self.text.append( svgfig.Text( x, cur_y, do[ 'name' ] ).SVG() )
            count += 1
            max_len = max( max_len, len( do['name' ] ) )
        self.widths[ order_index ] = max_len * 5.5
        self.max_x = max( self.max_x, left )
        self.max_y = max( self.max_y, top )
        self.max_width = max( self.max_width, self.widths[ order_index ] )
