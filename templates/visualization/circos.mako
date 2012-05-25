<%inherit file="/base.mako"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}

    ${h.js( "libs/d3", "mvc/visualization" )}

    <script type="text/javascript">
        $(function() {
            // -- Viz set up. --
            
            var genome = new Genome(JSON.parse('${ h.to_json_string( genome ) }')),
                dataset = new HistogramDataset(JSON.parse('${ h.to_json_string( dataset_summary ) }')),
                circos = new CircosView({
                    width: 600,
                    height: 600,
                    // Gap is difficult to set because it very dependent on chromosome size and organization.
                    total_gap: 2 * Math.PI * 0.5,
                    genome: genome,
                    dataset: dataset,
                    radius_start: 100,
                    dataset_arc_height: 50
                });
            
            // -- Render viz. --
                
            circos.render();
            $('body').append(circos.$el);                
        });
    </script>
</%def>

<%def name="body()">
    <h1>Circos plot for '${dataset.name}'</h1>
</%def>
