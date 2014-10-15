<%def name="init()">
<%
    ## create basic tool model
    tool_model = tool.to_dict(trans)
    tool_model['inputs'] = {}

    ## convert value to jsonifiable value
    def convert(v):
        # check if value is numeric
        isnumber = False
        try:
            float(v)
            isnumber = True
        except Exception:
            pass

        ## fix hda parsing
        if isinstance(v, HistoryDatasetAssociation):
            return {
                'id'  : trans.security.encode_id(v.id),
                'src' : 'hda'
            }
        elif isinstance(v, basestring) or isnumber:
            return v
        else:
            return None

    ## ensures that input dictionary is jsonifiable
    from collections import Iterable
    from galaxy.model import HistoryDatasetAssociation
    def sanitize(dict):
        ## quotations for Infinity so its jsonifiable
        for name in dict:
            if dict[name] == Infinity:
                dict[name] = 'Infinity'

        ## get current value
        value = dict['value'] if 'value' in dict else None

        ## identify lists
        if dict['type'] == 'data':
            if isinstance(value, list):
                value = [ convert(v) for v in value ]
            else:
                value = [ convert(value) ]
            value = {
                'batch'     : dict['multiple'],
                'values'    : value
            }
        elif isinstance(value, list):
            value = [ convert(v) for v in value ]
        else:
            value = convert(value)

        ## update and return
        dict['value'] = value
        return dict

    ## build model
    def build(group_inputs, inputs, tool_state, errors, other_values=None):
        from galaxy.util.expressions import ExpressionContext
        other_values = ExpressionContext( tool_state, other_values )
        for input_index, input in enumerate( inputs.itervalues() ):
            ## create model dictionary
            group_inputs[input_index] = input.to_dict(trans)

            ## identify stat for subsection/group
            group_state = tool_state[input.name]

            ## iterate and update values
            if input.type == "repeat":
                group_cache = group_inputs[input_index]['cache'] = {}
                for i in range( len( group_state ) ):
                    group_cache[i] = {}
                    group_errors = errors[input.name][i] if input.name in errors else dict()
                    build( group_cache[i], input.inputs, group_state[i], group_errors, other_values )
            elif input.type == "conditional":
                try:
                    test_param = group_inputs[input_index]['test_param']
                    test_param['value'] = group_state[test_param['name']]
                except Exception:
                    pass
                i = group_state['__current_case__']
                group_errors = errors.get( input.name, {} )
                build(group_inputs[input_index]['cases'][i]['inputs'], input.cases[i].inputs, group_state, group_errors, other_values)
            else:
                ## create input dictionary, try to pass other_values if to_dict function supports it e.g. dynamic options
                try:
                    group_inputs[input_index] = input.to_dict(trans, other_values=other_values)
                except Exception:
                    pass

                ## update input value from tool state
                try:
                    group_inputs[input_index]['value'] = tool_state[group_inputs[input_index]['name']]
                    group_inputs[input_index] = sanitize(group_inputs[input_index])
                except Exception:
                    pass
            endif
        endfor
    build(tool_model['inputs'], tool.inputs, tool_state.inputs, errors, "")

    # load tool help
    tool_help = ''
    if tool.help:
        if tool.has_multiple_pages:
            tool_help = tool.help_by_page[tool_state.page]
        else:
            tool_help = tool.help

        # Help is Mako template, so render using current static path.
        tool_help = tool_help.render( static_path=h.url_for( '/static' ), host_url=h.url_for('/', qualified=True) )

        # Convert to unicode to display non-ascii characters.
        if type( tool_help ) is not unicode:
            tool_help = unicode( tool_help, 'utf-8')
    endif

    # check if citations exist
    tool_citations = False
    if tool.citations:
        tool_citations = True

    # form configuration
    self.form_config = {
        'id'            : tool.id,
        'model'         : tool_model,
        'help'          : tool_help,
        'citations'     : tool_citations,
        'biostar_url'   : trans.app.config.biostar_url,
        'history_id'    : trans.security.encode_id( trans.history.id ),
        'job_id'        : trans.security.encode_id( job.id ) if job else None
    }
%>
</%def>

${ init() }
${ h.dumps(self.form_config) }