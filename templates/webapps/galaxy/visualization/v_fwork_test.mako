<%inherit file="/base.mako"/>
<%def name="title()">
${visualization_name}
</%def>


<%def name="stylesheets()">
${parent.stylesheets()}
${h.css(
    "base",
)}

<style type="text/css">
/*TODO: use/move into base.less*/
* { margin: 0px; padding: 0px; }
</style>
    
</%def>

<%def name="process_hda( hda )">
<%
    hda_dict = hda.get_api_value()
    hda_dict[ 'id' ] = trans.security.encode_id( hda_dict[ 'id' ] )
    hda_dict[ 'history_id' ] = trans.security.encode_id( hda_dict[ 'history_id' ] )
    del hda_dict[ 'peek' ]
    return hda_dict
%>
</%def>

<%def name="javascripts()">
${parent.javascripts()}
<script type="text/javascript">
$(function(){

//var data = {
//        title   : 'shared with user visualization',
//        type    : 'test',
//        slug    : 'shared',
//        annotation : 'a visualization shared with a specific user',
//        config  : {
//            x : 10,
//            y : 10
//        }
//    };

//var creationPromise = jQuery.ajax( '/api/visualizations', {
//        type        : 'POST',
//        contentType : 'application/json',
//        data        : JSON.stringify( data )
//    });
//creationPromise.success(function(){
//    console.debug( 'success' );
//});
//creationPromise.error(function(){
//    console.debug( 'error' );
//});


});
</script>
</%def>

<%def name="print_var( name, var )">
%if var is not None:
    <% t = str( type( var ) )[1:-1] %>
    <p>${name}: ${t}, ${var}</p>
%else:
    <p>No ${name}</p>
%endif
</%def>

<%def name="body()">
    <%
        import pprint
        print self
        print self.context
        pprint.pprint( self.context.kwargs, indent=4 )
    %>
    <%
        vars_to_print = [
            ( 'default', default ),
            ( 'string', string ),
            ( 'boolean', boolean ),
            ( 'integer', integer ),
            ( 'float', float ),
            ( 'json', json ),
        ]
    %>
    %for name, var in vars_to_print:
        ${print_var( name, var )}
    %endfor

    %if visualization:
        <h1>${visualization.title}</h1>
        <p>id: ${trans.security.encode_id( visualization.id )}</p>
        <p>dbkey: ${visualization.dbkey}</p>
        <p>config:
            <pre>${h.to_json_string( visualization.latest_revision.config, sort_keys=True, indent=( 4 * ' ' ) )}</pre>
        </p>
    %endif

    %if dataset:
        <h1>${dataset.name}</h1>
        <p>id: ${trans.security.encode_id( dataset.id )}</p>
        <p>history id: ${trans.security.encode_id( dataset.history.id )}</p>
        <pre>
            ${h.to_json_string( process_hda( dataset ), sort_keys=True, indent=( 4 * ' ' ) )}
        </pre>
    %endif

    %if dataset_instance:
        <h1>${dataset_instance.name}</h1>
        <p>id: ${trans.security.encode_id( dataset_instance.id )}</p>
        %if hda_ldda == 'hda':
        <p>history id: ${trans.security.encode_id( dataset_instance.history.id )}</p>
        <pre>
            ${h.to_json_string( process_hda( dataset_instance ), sort_keys=True, indent=( 4 * ' ' ) )}
        </pre>
        %else:
        <p>(LibraryDatasetDatasetAssociation)</p>
        %endif
    %endif

    %if query_args:
    <ul>
        %for key, val in query_args.items():
        <li>${key} : ${val}</li>
        %endfor
    </ul>
    %endif
    
</%def>
