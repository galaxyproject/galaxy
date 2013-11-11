/* =============================================================================
todo:
    Remove 'chart' names
    Make this (the config control/editor) and the ScatterplotView (in scatterplot.js) both
        views onto a visualization/revision model
    Move margins into wid/hi calcs (so final svg dims are w/h)
    Better separation of AJAX in scatterplot.js (maybe pass in function?)
    Labels should auto fill in chart control when dataset has column_names
    Allow column selection/config using the peek output as a base for UI
    Allow setting perPage of config
    Auto render if given data and/or config
    Allow option to auto set width/height based on screen real estate avail.
    Use d3.nest to allow grouping, pagination/filtration by group (e.g. chromCol)
    Semantic HTML (figure, caption)
    Save as visualization, load from visualization
    Save as SVG/png
    Does it work w/ Galaxy.Frame?
    Embedding
    Small multiples
    Drag & Drop other splots onto current (redraw with new axis and differentiate the datasets)
    
    Subclass on specific datatypes? (vcf, cuffdiff, etc.)
    What can be common/useful to other visualizations?

============================================================================= */
/**
 *  Scatterplot config control UI as a backbone view
 *      handles:
 *          configuring which data will be used
 *          configuring the plot display
 */
var ScatterplotConfigEditor = BaseView.extend( LoggableMixin ).extend({
    //TODO: !should be a view on a visualization model
    //logger      : console,
    className   : 'scatterplot-control-form',
    
    /** initialize requires a configuration Object containing a dataset Object */
    initialize : function( attributes ){
        //console.log( this + '.initialize, attributes:', attributes );
        if( !attributes || !attributes.config || !attributes.config.dataset ){
            throw new Error( "ScatterplotView requires a configuration and dataset" );
        }
        this.dataset = attributes.config.dataset;
        //console.log( 'dataset:', this.dataset );

        this.plotView = new ScatterplotView({
            config  : attributes.config
        });
    },

    // ------------------------------------------------------------------------- CONTROLS RENDERING
    render : function(){
        //console.log( this + '.render' );

        // render the tab controls, areas and loading indicator
        this.$el.append( ScatterplotConfigEditor.templates.mainLayout({
        }));

        // render the tab content
        this.$el.find( '#data-control'  ).append( this._render_dataControl() );
        this._render_chartControls( this.$el.find( '#chart-control' ) );
        //this.$statsDisplay  = this.$el.find( '.tab-pane#stats-display' );
        this._render_chartDisplay();

        //TODO: auto render if given both x, y column choices in query for page

        // set up behaviours
        this.$el.find( '[title]' ).tooltip();

        // uncomment any of the following to have that tab show on initial load (for testing)
        //this.$el.find( 'ul.nav' ).find( 'a[href="#data-control"]' ).tab( 'show' );
        //this.$el.find( 'ul.nav' ).find( 'a[href="#chart-control"]' ).tab( 'show' );
        //this.$el.find( 'ul.nav' ).find( 'a[href="#stats-display"]' ).tab( 'show' );
        //this.$el.find( 'ul.nav' ).find( 'a[href="#chart-display"]' ).tab( 'show' );
        return this;
    },

    _render_dataControl : function(){
        // controls for which columns are used to plot datapoints (and ids/additional info to attach if desired)
        var dataset = this.dataset;
        //console.log( 'metadata_column_types:', this.dataset.metadata_column_types );
        //console.log( 'metadata_column_names:', this.dataset.metadata_column_names );

        var allColumns = _.map( dataset.metadata_column_types, function( type, i ){
            var column = { index: i, type: type, name: ( 'column ' + ( i + 1 ) ) };
            if( dataset.metadata_column_names && dataset.metadata_column_names[ i ] ){
                column.name = dataset.metadata_column_names[ i ];
            }
            return column;
        });
        var numericColumns = _.filter( allColumns, function( column, i ){
            return ( ( column.type === 'int' ) || ( column.type === 'float' ) );
        });
        if( numericColumns < 2 ){
            numericColumns = allColumns;
        }
        //console.log( 'allColumns:', allColumns );
        //console.log( 'numericColumns:', numericColumns );

        // render the html
        var $dataControl = this.$el.find( '.tab-pane#data-control' );
        $dataControl.html( ScatterplotConfigEditor.templates.dataControl({
            allColumns      : allColumns,
            numericColumns  : numericColumns
        }));

        // preset to column selectors if they were passed in the config in the query string
        $dataControl.find( '[name="xColumn"]' ).val( this.plotView.config.xColumn || numericColumns[0].index );
        $dataControl.find( '[name="yColumn"]' ).val( this.plotView.config.yColumn || numericColumns[1].index );
        if( this.plotView.config.idColumn !== undefined ){
            $dataControl.find( '#include-id-checkbox' ).prop( 'checked', true ).trigger( 'change' );
            $dataControl.find( 'select[name="idColumn"]' ).val( this.plotView.config.idColumn );
        }

        return $dataControl;
    },
    
    _render_chartControls : function( $chartControls ){
        // tab content to control how the chart is rendered (data glyph size, chart size, etc.)
        $chartControls.html( ScatterplotConfigEditor.templates.chartControl( this.plotView.config ) );
        //console.debug( '$chartControl:', $chartControls );

        // set up behaviours, js on sliders
        //console.debug( 'numeric sliders:', $chartControls.find( '.numeric-slider-input' ) );
        // what to do when the slider changes: update display and update chartConfig
        var view = this,
            // limits for controls (by control/chartConfig id)
            //TODO: move into TwoVarScatterplot
            controlRanges = {
                'datapointSize' : { min: 2, max: 10, step: 1 },
                'width'         : { min: 200, max: 800, step: 20 },
                'height'        : { min: 200, max: 800, step: 20 }
            };

        function onSliderChange(){
            var $this = $( this );
            $this.siblings( '.slider-output' ).text( $this.slider( 'value' ) );
        }
        $chartControls.find( '.numeric-slider-input' ).each( function(){
            var $this = $( this ),
                configKey = $this.attr( 'data-config-key' ),
                sliderSettings = _.extend( controlRanges[ configKey ], {
                    value   : view.plotView.config[ configKey ],
                    change  : onSliderChange,
                    slide   : onSliderChange
                });
            //console.debug( configKey + ' slider settings:', sliderSettings );
            $this.find( '.slider' ).slider( sliderSettings );
        });
//TODO: to more common area (like render)?
        // set label inputs to current x, y metadata_column_names (if any)
        if( this.dataset.metadata_column_names ){
            //var colNames = this.dataset.metadata_column_names;
            //$chartControls.find( 'input[name="X-axis-label"]' ).val( colNames );
            //$chartControls.find( 'input[name="Y-axis-label"]' ).val( colNames );
//TODO: on change of x, y data controls
        }

        //console.debug( '$chartControls:', $chartControls );
        return $chartControls;
    },

    _render_chartDisplay : function(){
        // render the tab content where the chart is displayed (but not the chart itself)
        var $chartDisplay = this.$el.find( '.tab-pane#chart-display' );
        this.plotView.setElement( $chartDisplay );
        this.plotView.render();
        return $chartDisplay;
    },

    // ------------------------------------------------------------------------- EVENTS
    events : {
        'change #include-id-checkbox'          : 'toggleThirdColumnSelector',
        'click #data-control .render-button'   : 'renderChart',
        'click #chart-control .render-button'  : 'renderChart'
    },

    toggleThirdColumnSelector : function(){
        // show/hide the id selector on the data settings panel
        this.$el.find( 'select[name="idColumn"]' ).parent().toggle();
    },

    // ------------------------------------------------------------------------- CHART/STATS RENDERING
    renderChart : function(){
        //console.log( this + '.renderChart' );
        // fetch the data, (re-)render the chart
        this.$el.find( '.nav li.disabled' ).removeClass( 'disabled' );
        this.updateConfigWithDataSettings();
        this.updateConfigWithChartSettings();
        this.$el.find( 'ul.nav' ).find( 'a[href="#chart-display"]' ).tab( 'show' );
        this.plotView.fetchData();
        //console.debug( this.plotView.$el );
    },

    // ------------------------------------------------------------------------- GET DATA/CHART SETTINGS
    updateConfigWithDataSettings : function(){
        // parse the column values for both indeces (for the data fetch) and names (for the chart)
        var $dataControls = this.$el.find( '#data-control' );
        var settings = {
            xColumn : $dataControls.find( '[name="xColumn"]' ).val(),
            yColumn : $dataControls.find( '[name="yColumn"]' ).val()
        };
        if( $dataControls.find( '#include-id-checkbox' ).prop( 'checked' ) ){
            settings.idColumn = $dataControls.find( '[name="idColumn"]' ).val();
        }
        //console.log( '\t data settings:', settings );
        return _.extend( this.plotView.config, settings );
    },

    updateConfigWithChartSettings : function(){
        // gets the user-selected chartConfig from the chart settings panel
        var plotView = this.plotView,
            $chartControls = this.$el.find( '#chart-control' );
        // use a loop of config keys to get the form values for these sliders
        [ 'datapointSize', 'width', 'height' ].forEach( function( v, i ){
            plotView.config[ v ] = $chartControls.find( '.numeric-slider-input[data-config-key="' + v + '"]' )
                .find( '.slider' ).slider( 'value' );
        });
        // update axes labels using chartSettings inputs (if not at defaults), otherwise the selects' colName
        plotView.config.x.label = $chartControls.find( 'input[name="X-axis-label"]' ).val();
        plotView.config.y.label = $chartControls.find( 'input[name="Y-axis-label"]' ).val();
        //console.log( '\t chartSettings:', settings );
        return plotView.config;
    },

    toString : function(){
        return 'ScatterplotConfigEditor(' + (( this.dataset )?( this.dataset.id ):( '' )) + ')';
    }
});

ScatterplotConfigEditor.templates = {
    mainLayout      : Templates.editor,
    dataControl     : Templates.datacontrol,
    chartControl    : Templates.chartcontrol
};

//==============================================================================
