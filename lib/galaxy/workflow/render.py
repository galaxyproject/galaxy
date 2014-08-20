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

        self.data = []

    def finish( self ):
        max_x, max_y, max_width = self.max_x, self.max_y, self.max_width

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

    def add_connection( self, step_dict, conn, output_dict):
        margin = MARGIN

        in_coords = self.in_pos[ step_dict[ 'id' ] ][ conn ]
        # out_pos_index will be a step number like 1, 2, 3...
        out_pos_index = output_dict[ 'id' ]
        # out_pos_name will be a string like 'o', 'o2', etc.
        out_pos_name = output_dict[ 'output_name' ]
        if out_pos_index in self.out_pos:
            # out_conn_index_dict will be something like:
            # 7: {'o': (824.5, 618)}
            out_conn_index_dict = self.out_pos[ out_pos_index ]
            if out_pos_name in out_conn_index_dict:
                out_conn_pos = out_conn_index_dict[ out_pos_name ]
            else:
                # Take any key / value pair available in out_conn_index_dict.
                # A problem will result if the dictionary is empty.
                if out_conn_index_dict.keys():
                    key = out_conn_index_dict.keys()[0]
                    out_conn_pos = self.out_pos[ out_pos_index ][ key ]
        adjusted = ( out_conn_pos[ 0 ] + self.widths[ output_dict[ 'id' ] ], out_conn_pos[ 1 ] )
        self.text.append( svgfig.SVG( "circle",
                                      cx=out_conn_pos[ 0 ] + self.widths[ output_dict[ 'id' ] ] - margin,
                                      cy=out_conn_pos[ 1 ] - margin,
                                      r=5,
                                      fill="#ffffff" ) )
        self.connectors.append( svgfig.Line( adjusted[ 0 ],
                                             adjusted[ 1 ] - margin,
                                             in_coords[ 0 ] - 10,
                                             in_coords[ 1 ],
                                             arrow_end="true" ).SVG() )

    def add_steps( self, highlight_errors=False ):
        # Only highlight missing tools if displaying in the tool shed.
        for step_dict in self.data:
            tool_unavailable = step_dict.get( 'tool_errors', False )
            if highlight_errors and tool_unavailable:
                fill = "#EBBCB2"
            else:
                fill = "#EBD9B2"

            width = self.widths[ step_dict[ 'id' ] ]
            self.add_boxes( step_dict, width, fill )
            for conn, output_dict in step_dict[ 'input_connections' ].iteritems():
                self.add_connection( step_dict, conn, output_dict )

    def populate_data_for_step( self, step, module_name, module_data_inputs, module_data_outputs, tool_errors=None ):
        step_dict = {
            'id': step.order_index,
            'data_inputs': module_data_inputs,
            'data_outputs': module_data_outputs,
            'position': step.position
        }
        if tool_errors:
            step_dict[ 'tool_errors' ] = tool_errors

        input_conn_dict = {}
        for conn in step.input_connections:
            input_conn_dict[ conn.input_name ] = \
                dict( id=conn.output_step.order_index, output_name=conn.output_name )
        step_dict['input_connections'] = input_conn_dict

        self.data.append(step_dict)
        self.add_text( module_data_inputs, module_data_outputs, step, module_name )
