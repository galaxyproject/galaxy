/* =============================================================================
todo:
    I'd like to move the svg creation out of the splot constr. to:
        allow adding splots to an existing canvas
        allow mult. splots sharing a canvas


    outside this:
        BUG: setting width, height in plot controls doesn't re-interpolate data locations!!
        BUG?: get metadata_column_names (from datatype if necessary)
        BUG: single vis in popupmenu should have tooltip with that name NOT 'Visualizations'
    
    wire label setters, anim setter
    
    TwoVarScatterplot:
        ??: maybe better to do this with a canvas...
        save as visualization
        to seperate file?
        remove underscore dependencies
        add interface to change values (seperate)?
        download svg -> base64 encode
        incorporate glyphs, glyph state renderers
        
    ScatterplotSettingsForm:
        some css bug that lowers the width of settings form when plot-controls tab is open
            causes chart to shift
        what can be abstracted/reused for other graphs?
        avoid direct manipulation of this.plot
        allow option to put plot into seperate tab of interface (for small multiples)
    
        provide callback in view to load data incrementally - for large sets
            paginate
                handle rerender
                use endpoint (here and on the server (fileptr))
            fetch (new?) data
                handle rerender
            use d3.TSV?
            render warning on long data (> maxDataPoints)
                adjust endpoint
        
        selectable list of preset column comparisons (rnaseq etc.)
            how to know what sort of Tabular the data is?
        smarter about headers
        validate columns selection (here or server)

        set stats column names by selected columns
        move chart into tabbed area...
        
    Scatterplot.mako:
        multiple plots on one page (small multiples)
        ?? ensure svg styles thru d3 or css?
            d3: configable (easily)
            css: standard - better maintenance
            ? override at config

============================================================================= */
/**
 *  Scatterplot control UI as a backbone view
 *      handles:
 *          getting the desired data
 *          configuring the plot display
 *          showing (general) statistics
 *
 *  initialize attributes REQUIRES a dataset and an apiDatasetsURL
 */
var ScatterplotControlForm = BaseView.extend( LoggableMixin ).extend({
    //logger      : console,
    className   : 'scatterplot-control-form',
    
    dataLoadDelay : 500,
    dataLoadSize  : 3001,

    loadingIndicatorImage : 'loading_small_white_bg.gif',
    fetchMsg    : 'Fetching data...',
    renderMsg   : 'Rendering...',
    
    initialize : function( attributes ){
        this.log( this + '.initialize, attributes:', attributes );
        
        this.dataset = null;
        this.chartConfig = null;
        this.chart = null;
        this.loader = null;

        // set up refs to the four tab areas
        this.$dataControl = null;
        this.$chartControl = null;
        this.$statsDisplay = null;
        this.$chartDisplay = null;

        this.dataFetch = null;

        this.initializeFromAttributes( attributes );
        this.initializeChart( attributes );
        this.initializeDataLoader( attributes );
    },

    initializeFromAttributes : function( attributes ){
        // required settings: ensure certain vars we need are passed in attributes
        if( !attributes || !attributes.dataset ){
            throw( "ScatterplotView requires a dataset" );
        } else {
            this.dataset = attributes.dataset;
        }
        if( jQuery.type( this.dataset.metadata_column_types ) === 'string' ){
            this.dataset.metadata_column_types = this.dataset.metadata_column_types.split( ', ' );
        }
        this.log( '\t dataset:', this.dataset );

        // passed from mako helper
        //TODO: integrate to galaxyPaths
        //TODO: ?? seems like data loader section would be better
        if( !attributes.apiDatasetsURL ){
            throw( "ScatterplotView requires a apiDatasetsURL" );
        } else {
            this.dataURL = attributes.apiDatasetsURL + '/' + this.dataset.id + '?';
        }
        this.log( '\t dataURL:', this.dataURL );
    },

    initializeChart : function( attributes ){
        // set up the basic chart infrastructure and config (if any)
        this.chartConfig = attributes.chartConfig || {};
        //if( this.logger ){ this.chartConfig.debugging = true; }
        this.log( '\t initial chartConfig:', this.chartConfig );

        this.chart = new TwoVarScatterplot( this.chartConfig );
        //TODO: remove 2nd ref, use this.chart.config
        this.chartConfig = this.chart.config;
    },

    initializeDataLoader : function( attributes ){
        // set up data loader
        var view = this;
        this.loader = new LazyDataLoader({
            //logger  : ( this.logger )?( this.logger ):( null ),
            // we'll generate this when columns are chosen
            url     : null,
            start   : attributes.start || 0,
            //NOTE: metadata_data_lines can be null (so we won't know the total)
            total   : attributes.total || this.dataset.metadata_data_lines,
            delay   : this.dataLoadDelay,
            size    : this.dataLoadSize,

            buildUrl : function( start, size ){
                // currently VERY SPECIFIC to using data_providers.py start_val, max_vals params
                return this.url + '&' + jQuery.param({
                    start_val: start,
                    max_vals:  size
                });
            }
        });
        $( this.loader ).bind( 'error', function( event, status, error ){
            view.log( 'ERROR:', status, error );
            alert( 'ERROR fetching data:\n' + status + '\n' + error );
            view.hideLoadingIndicator();
        });
    },
    
    // ------------------------------------------------------------------------- CONTROLS RENDERING
    render : function(){
        this.log( this + '.render' );

        // render the tab controls, areas and loading indicator
        this.$el.append( ScatterplotControlForm.templates.mainLayout({
            loadingIndicatorImagePath   : galaxy_paths.get( 'image_path' ) + '/' + this.loadingIndicatorImage,
            message                     : ''
        }));

        // render the tab content
        this.$dataControl   = this._render_dataControl();
        this.$chartControl  = this._render_chartControl();
        this.$statsDisplay  = this.$el.find( '.tab-pane#stats-display' );
        this.$chartDisplay  = this._render_chartDisplay();

        // auto render if given both x, y column choices in query for page
        //TODO:?? add autoRender=1 to query maybe?
        if( this.chartConfig.xColumn && this.chartConfig.yColumn ){
            this.renderChart();
        }

        // set up behaviours
        this.$el.find( '.tooltip' ).tooltip();

        // uncomment any of the following to have that tab show on initial load (for testing)
        //this.$el.find( 'ul.nav' ).find( 'a[href="#data-control"]' ).tab( 'show' );
        //this.$el.find( 'ul.nav' ).find( 'a[href="#chart-control"]' ).tab( 'show' );
        //this.$el.find( 'ul.nav' ).find( 'a[href="#stats-display"]' ).tab( 'show' );
        //this.$el.find( 'ul.nav' ).find( 'a[href="#chart-display"]' ).tab( 'show' );
        return this;
    },

    _render_dataControl : function(){
        // controls for which columns are used to plot datapoints (and ids/additional info to attach if desired)
        var view = this,
            allColumns = [],
            numericColumns = [];
        
        // gather column indeces (from metadata_column_types) and names (from metadata_columnnames)
        _.each( this.dataset.metadata_column_types, function( type, index ){
            // use a 1 based index in names/values within the form (will be dec. when parsed out)
            var oneBasedIndex = index + 1,
                // label with the name if available (fall back on 'column <index>')
                name = 'column ' + oneBasedIndex;
            if( view.dataset.metadata_column_names ){
                name = view.dataset.metadata_column_names[ index ];
            }
            
            // cache all columns here
            allColumns.push({ index: oneBasedIndex, name: name });

            // filter numeric columns to their own list
            if( type === 'int' || type === 'float' ){
                numericColumns.push({ index: oneBasedIndex, name: name });
            }
        });
        //TODO: other vals: max_vals, start_val, pagination (chart-settings)
            
        // render the html
        var $dataControl = this.$el.find( '.tab-pane#data-control' );
        $dataControl.append( ScatterplotControlForm.templates.dataControl({
            allColumns      : allColumns,
            numericColumns  : numericColumns
        }));

        // preset to column selectors if they were passed in the config in the query string
        $dataControl.find( '#X-select' ).val( this.chartConfig.xColumn );
        $dataControl.find( '#Y-select' ).val( this.chartConfig.yColumn );
        if( this.chartConfig.idColumn !== undefined ){
            $dataControl.find( '#include-id-checkbox' )
                .attr( 'checked', true ).trigger( 'change' );
            $dataControl.find( '#ID-select' ).val( this.chartConfig.idColumn );
        }

        return $dataControl;
    },
    
    _render_chartControl : function(){
        // tab content to control how the chart is rendered (data glyph size, chart size, etc.)
        var view = this,
            $chartControl = this.$el.find( '.tab-pane#chart-control' ),
            // limits for controls (by control/chartConfig id)
            //TODO: move into TwoVarScatterplot
            controlRanges = {
                'datapointSize' : { min: 2, max: 10, step: 1 },
                'width'         : { min: 200, max: 800, step: 20 },
                'height'        : { min: 200, max: 800, step: 20 }
            };

        // render the html
        $chartControl.append( ScatterplotControlForm.templates.chartControl( this.chartConfig ) );

        // set up behaviours, js on sliders
        $chartControl.find( '.numeric-slider-input' ).each( function(){
            var $this = $( this ),
                $output = $this.find( '.slider-output' ),
                $slider = $this.find( '.slider' ),
                id = $this.attr( 'id' );
            //chartControl.log( 'slider set up', 'this:', $this, 'slider:', $slider, 'id', id );

            // what to do when the slider changes: update display and update chartConfig
            //TODO: move out of loop
            function onSliderChange(){
                var $this = $( this ),
                    newValue = $this.slider( 'value' );
                //chartControl.log( 'slider change', 'this:', $this, 'output:', $output, 'value', newValue );
                $output.text( newValue );
                //chartControl.chartConfig[ id ] = newValue;
            }

            $slider.slider( _.extend( controlRanges[ id ], {
                value   : view.chartConfig[ id ],
                change  : onSliderChange,
                slide   : onSliderChange
            }));
        });

        return $chartControl;
    },

    _render_chartDisplay : function(){
        // render the tab content where the chart is displayed (but not the chart itself)
        var $chartDisplay = this.$el.find( '.tab-pane#chart-display' );
        $chartDisplay.append( ScatterplotControlForm.templates.chartDisplay( this.chartConfig ) );
        return $chartDisplay;
    },

    // ------------------------------------------------------------------------- EVENTS
    events : {
        'change #include-id-checkbox'          : 'toggleThirdColumnSelector',
        'click #data-control #render-button'   : 'renderChart',
        'click #chart-control #render-button'  : 'changeChartSettings'
    },

    toggleThirdColumnSelector : function(){
        // show/hide the id selector on the data settings panel
        this.$el.find( 'select[name="ID"]' ).parent().toggle();
    },
    
    showLoadingIndicator : function( message, callback ){
        // display the loading indicator over the tab panels if hidden, update message (if passed)
        message = message || '';
        var indicator = this.$el.find( 'div#loading-indicator' );
            messageBox = indicator.find( '.loading-message' );
            
        if( indicator.is( ':visible' ) ){
            if( message ){
                messageBox.fadeOut( 'fast', function(){
                    messageBox.text( message );
                    messageBox.fadeIn( 'fast', callback );
                });
            } else {
                callback();
            }
            
        } else {
            if( message ){ messageBox.text( message ); }
            indicator.fadeIn( 'fast', callback );
        }
    },

    hideLoadingIndicator : function( callback ){
        this.$el.find( 'div#loading-indicator' ).fadeOut( 'fast', callback );
    },
    
    // ------------------------------------------------------------------------- CHART/STATS RENDERING
    renderChart : function(){
        // fetch the data, (re-)render the chart
        this.log( this + '.renderChart' );

        //TODO: separate data fetch

        // this is a complete re-render, so clear the prev. data
        this.data = null;
        this.meta = null;
        
        // update the chartConfig (here and chart) using chart settings
        //TODO: separate and improve (used in changeChartSettings too)
        _.extend( this.chartConfig, this.getChartSettings() );
        this.log( '\t chartConfig:', this.chartConfig );
        this.chart.updateConfig( this.chartConfig, false );
        
        // build the url with the current data settings
        this.loader.url = this.dataURL + '&' + jQuery.param( this.getDataSettings() );
        this.log( '\t loader: total lines:', this.loader.total, ' url:', this.loader.url );

        // bind the new data event to: aggregate data, update the chart and stats with new data
        var view = this;
        $( this.loader ).bind( 'loaded.new', function( event, response ){
            view.log( view + ' loaded.new', response );

            // aggregate data and meta
            view.postProcessDataFetchResponse( response );
            view.log( '\t postprocessed data:', view.data );
            view.log( '\t postprocessed meta:', view.meta );

            // update the chart and stats
            view.showLoadingIndicator( view.renderMsg, function(){
                view.chart.render( view.data, view.meta );
                view.renderStats( view.data, view.meta );
                view.hideLoadingIndicator();
            });
        });
        // when all data loaded - unbind (or we'll start doubling event handlers)
        $( this.loader ).bind( 'complete', function( event, data ){
            view.log( view + ' complete', data );
            $( view.loader ).unbind();
        });

        // begin loading the data, switch to the chart display tab
        view.showLoadingIndicator( view.fetchMsg, function(){
            view.$el.find( 'ul.nav' ).find( 'a[href="#chart-display"]' ).tab( 'show' );
            view.loader.load();
        });
    },

    renderStats : function(){
        this.log( this + '.renderStats' );
        // render the stats table in the stats panel
        //TODO: there's a better way
        this.$statsDisplay.html( ScatterplotControlForm.templates.statsDisplay({
            stats:  [
                { name: 'Count',    xval: this.meta[0].count,   yval: this.meta[1].count },
                { name: 'Min',      xval: this.meta[0].min,     yval: this.meta[1].min },
                { name: 'Max',      xval: this.meta[0].max,     yval: this.meta[1].max },
                { name: 'Sum',      xval: this.meta[0].sum,     yval: this.meta[1].sum },
                { name: 'Mean',     xval: this.meta[0].mean,    yval: this.meta[1].mean },
                { name: 'Median',   xval: this.meta[0].median,  yval: this.meta[1].median }
            ]
        }));
    },

    changeChartSettings : function(){
        // re-render the chart with new chart settings and OLD data
        var view = this;
            newChartSettings = this.getChartSettings();

        // update the chart config from the chartSettings panel controls
        _.extend( this.chartConfig, newChartSettings );
        this.log( 'this.chartConfig:', this.chartConfig );
        this.chart.updateConfig( this.chartConfig, false );

        // if there's current data, call chart.render with it (no data fetch)
        if( view.data && view.meta ){
            view.showLoadingIndicator( view.renderMsg, function(){
                view.$el.find( 'ul.nav' ).find( 'a[href="#chart-display"]' ).tab( 'show' );
                view.chart.render( view.data, view.meta );
                view.hideLoadingIndicator();
            });

        // no current data, call renderChart instead (which will fetch data)
        } else {
            this.renderChart();
        }
    },

    // ------------------------------------------------------------------------- DATA AGGREGATION
    postProcessDataFetchResponse : function( response ){
        // the loader only returns new data - it's up to this to munge the fetches together properly
        //TODO: we're now storing data in two places: loader and here
        //  can't we reduce incoming data into loader.data[0]? are there concurrency problems?
        this.postProcessData( response.data );
        this.postProcessMeta( response.meta );
    },
    
    postProcessData : function( newData ){
        // stack the column data on top of each other into this.data
        //this.log( this + '.postProcessData:', newData );
        var view = this;

        // if we already have data: aggregate
        if( view.data ){
            _.each( newData, function( newColData, colIndex ){
                //view.log( colIndex + ' data:', newColData );
                //TODO??: time, space efficiency of this?
                view.data[ colIndex ] = view.data[ colIndex ].concat( newColData );
            });
            
        // otherwise: assign (first load)
        } else {
            view.data = newData;
        }
    },

    postProcessMeta : function( newMeta ){
        // munge the meta data (stats) from the server fetches together
        //pre: this.data must be preprocessed (needed for medians)
        //this.log( this + '.postProcessMeta:', newMeta );
        var view = this,
            colTypes = this.dataset.metadata_column_types;

        // if we already have meta: aggregate
        if( view.meta ){
            _.each( newMeta, function( newColMeta, colIndex ){
                var colMeta = view.meta[ colIndex ],
                    colType = colTypes[ colIndex ];
                //view.log( '\t ' + colIndex + ' postprocessing meta:', newColMeta );
                //view.log( colIndex + ' old meta:',
                //    'min:',     colMeta.min,
                //    'max:',     colMeta.max,
                //    'sum:',     colMeta.sum,
                //    'mean:',    colMeta.mean,
                //    'median:',  colMeta.median
                //);

                //!TODO: at what point are we getting int/float overflow on these?!
                //??: need to be null safe?
                colMeta.count += ( newColMeta.count )?( newColMeta.count ):( 0 );
                //view.log( colIndex, 'count:', colMeta.count );
                
                if( ( colType === 'int' ) || ( colType === 'float' ) ){
                    //view.log( colIndex + ' incoming meta:',
                    //    'min:',     newColMeta.min,
                    //    'max:',     newColMeta.max,
                    //    'sum:',     newColMeta.sum,
                    //    'mean:',    newColMeta.mean,
                    //    'median:',  newColMeta.median
                    //);

                    colMeta.min  = Math.min( newColMeta.min, colMeta.min );
                    colMeta.max  = Math.max( newColMeta.max, colMeta.max );
                    colMeta.sum  = newColMeta.sum + colMeta.sum;
                    colMeta.mean = ( colMeta.count )?( colMeta.sum / colMeta.count ):( null );

                    // median's a pain bc of sorting (requires the data as well)
                    var sortedCol = view.data[ colIndex ].slice().sort(),
                        middleIndex = Math.floor( sortedCol.length / 2 );

                    if( sortedCol.length % 2 === 0 ){
                        colMeta.median = ( ( sortedCol[ middleIndex ] + sortedCol[( middleIndex + 1 )] ) / 2 );

                    } else {
                        colMeta.median = sortedCol[ middleIndex ];
                    }

                    //view.log( colIndex + ' new meta:',
                    //    'min:',     colMeta.min,
                    //    'max:',     colMeta.max,
                    //    'sum:',     colMeta.sum,
                    //    'mean:',    colMeta.mean,
                    //    'median:',  colMeta.median
                    //);
                }
            });

        // otherwise: assign (first load)
        } else {
            view.meta = newMeta;
            //view.log( '\t meta (first load):', view.meta );
        }
    },

    // ------------------------------------------------------------------------- GET DATA/CHART SETTINGS
    getDataSettings : function(){
        // parse the column values for both indeces (for the data fetch) and names (for the chart)
        var columnSelections = this.getColumnSelections(),
            columns = [];
        this.log( '\t columnSelections:', columnSelections );
            
        //TODO: validate columns - minimally: we can assume either set by selectors or via a good query string

        // get column indices for params, include the desired ID column (if any)
        //NOTE: these are presented in human-readable 1 base index (to match the data.peek) - adjust
        columns = [
            columnSelections.X.colIndex - 1,
            columnSelections.Y.colIndex - 1
        ];
        if( this.$dataControl.find( '#include-id-checkbox' ).attr( 'checked' ) ){
            columns.push( columnSelections.ID.colIndex - 1 );
        }
        //TODO: other vals: max, start, page
        
        var params = {
            data_type   : 'raw_data',
            columns     : '[' + columns + ']'
        };
        this.log( '\t data settings (url params):', params );
        return params;
    },

    getColumnSelections : function(){
        // gets the current user-selected values for which columns to fetch from the data settings panel
        // returns a map: { column-select name (eg. X) : { colIndex : column-selector val,
        //                                                 colName : selected option text }, ... }
        var selections = {};
        this.$dataControl.find( 'div.column-select select' ).each( function(){
            var $this   = $( this ),
                val     = $this.val();
            selections[ $this.attr( 'name' ) ] = {
                colIndex : val,
                colName  : $this.children( '[value="' + val + '"]' ).text()
            };
        });
        return selections;
    },

    getChartSettings : function(){
        // gets the user-selected chartConfig from the chart settings panel
        var settings = {},
            colSelections = this.getColumnSelections();
        //this.log( 'colSelections:', colSelections );

        //TODO: simplify with keys and loop
        settings.datapointSize = this.$chartControl.find( '#datapointSize.numeric-slider-input' )
            .find( '.slider' ).slider( 'value' );
        settings.width = this.$chartControl.find( '#width.numeric-slider-input' )
            .find( '.slider' ).slider( 'value' );
        settings.height = this.$chartControl.find( '#height.numeric-slider-input' )
            .find( '.slider' ).slider( 'value' );

        // update axes labels using chartSettings inputs (if not at defaults), otherwise the selects' colName
        //TODO: a little confusing
        var chartSettingsXLabel = this.$chartControl.find( 'input#X-axis-label' ).val(),
            chartSettingsYLabel = this.$chartControl.find( 'input#Y-axis-label' ).val();
        settings.xLabel = ( chartSettingsXLabel === 'X' )?
                            ( colSelections.X.colName ):( chartSettingsXLabel );
        settings.yLabel = ( chartSettingsYLabel === 'Y' )?
                            ( colSelections.Y.colName ):( chartSettingsYLabel );

        settings.animDuration = 10;
        if( this.$chartControl.find( '#animDuration.checkbox-input' ).is( ':checked' ) ){
            settings.animDuration = 500;
        }

        this.log( '\t chartSettings:', settings );
        return settings;
    },

    toString : function(){
        return 'ScatterplotControlForm(' + (( this.dataset )?( this.dataset.id ):( '' )) + ')';
    }
});

ScatterplotControlForm.templates = {
    mainLayout      : Handlebars.templates[ 'template-visualization-scatterplotControlForm' ],
    dataControl     : Handlebars.templates[ 'template-visualization-dataControl' ],
    chartControl    : Handlebars.templates[ 'template-visualization-chartControl' ],
    statsDisplay    : Handlebars.templates[ 'template-visualization-statsDisplay' ],
    chartDisplay    : Handlebars.templates[ 'template-visualization-chartDisplay' ]
};

//==============================================================================
