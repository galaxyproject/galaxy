<%inherit file="/base.mako"/>
<%def name="title()">${ history.name } | ${ _( 'Citations' ) }</%def>
<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style type="text/css">
    </style>
</%def>

## ----------------------------------------------------------------------------
<%def name="javascripts()">
    ${h.js( "libs/bibtex" )}
<%
    self.js_app = 'display-citations'   
    history_id = trans.security.encode_id( history.id )
%>
    ${parent.javascripts()}

    ## load edit views for each of the hdas
    <script type="text/javascript">
        define( 'display-citations', function(){
            require(["mvc/citation/citation-model", "mvc/citation/citation-view"
            ], function( citationModel, citationView ){
                $(function() {
                    var citations = new citationModel.HistoryCitationCollection();
                    citations.history_id = "${history_id}";
                    var citation_list_view = new citationView.CitationListView({ collection: citations } );
                    citation_list_view.render();
                    citations.fetch();
                } );
            } );
        });
    </script>
</%def>
<div id="citations">
</div>
