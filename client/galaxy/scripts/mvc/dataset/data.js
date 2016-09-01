// Additional dependencies: jQuery, underscore.
define(['mvc/ui/ui-modal', 'mvc/ui/ui-frames', 'mvc/ui/icon-button'], function(Modal, Frames, mod_icon_btn) {

/**
 * Dataset metedata.
 */
var DatasetMetadata = Backbone.Model.extend({});

/**
 * A dataset. In Galaxy, datasets are associated with a history, so
 * this object is also known as a HistoryDatasetAssociation.
 */
var Dataset = Backbone.Model.extend({
    defaults: {
        id: '',
        type: '',
        name: '',
        hda_ldda: 'hda',
        metadata: null
    },

    initialize: function() {
        // Metadata can be passed in as a model or a set of attributes; if it's
        // already a model, there's no need to set metadata.
        if (!this.get('metadata')) {
            this._set_metadata();
        }

        // Update metadata on change.
        this.on('change', this._set_metadata, this);
    },

    _set_metadata: function() {
        var metadata = new DatasetMetadata();

        // Move metadata from dataset attributes to metadata object.
        _.each(_.keys(this.attributes), function(k) {
            if (k.indexOf('metadata_') === 0) {
                // Found metadata.
                var new_key = k.split('metadata_')[1];
                metadata.set(new_key, this.attributes[k]);
                delete this.attributes[k];
            }
        }, this);

        // Because this is an internal change, silence it.
        this.set('metadata', metadata, { 'silent': true });
    },

    /**
     * Returns dataset metadata for a given attribute.
     */
    get_metadata: function(attribute) {
        return this.attributes.metadata.get(attribute);
    },

    urlRoot: Galaxy.root + "api/datasets"
});

/**
 * A tabular dataset. This object extends dataset to provide incremental chunked data.
 */
var TabularDataset = Dataset.extend({
    defaults: _.extend({}, Dataset.prototype.defaults, {
        chunk_url: null,
        first_data_chunk: null,
        offset: 0,
        at_eof: false
    }),

    initialize: function(options) {
        Dataset.prototype.initialize.call(this);

        // If first data chunk is available, next chunk is 1.
        if (this.attributes.first_data_chunk){
            this.attributes.offset = this.attributes.first_data_chunk.offset;
        }
        this.attributes.chunk_url = Galaxy.root + 'dataset/display?dataset_id=' + this.id;
        this.attributes.url_viz = Galaxy.root + 'visualization';
    },

    /**
     * Returns a jQuery Deferred object that resolves to the next data chunk or null if at EOF.
     */
    get_next_chunk: function() {
        // If already at end of file, do nothing.
        if (this.attributes.at_eof) {
            return null;
        }

        // Get next chunk.
        var self = this,
            next_chunk = $.Deferred();
        $.getJSON(this.attributes.chunk_url, {
            offset: self.attributes.offset
        }).success(function(chunk) {
            var rval;
            if (chunk.ck_data !== '') {
                // Found chunk.
                rval = chunk;
                self.attributes.offset = chunk.offset;
            }
            else {
                // At EOF.
                self.attributes.at_eof = true;
                rval = null;
            }
            next_chunk.resolve(rval);
        });

        return next_chunk;
    }
});

var DatasetCollection = Backbone.Collection.extend({
    model: Dataset
});

/**
 * Provides a base for table-based, dynamic view of a tabular dataset.
 * Do not instantiate directly; use either TopLevelTabularDatasetChunkedView
 * or EmbeddedTabularDatasetChunkedView.
 */
var TabularDatasetChunkedView = Backbone.View.extend({

    /**
     * Initialize view and, importantly, set a scroll element.
     */
    initialize: function(options) {
        // Row count for rendering.
        this.row_count = 0;
        this.loading_chunk = false;

        // load trackster button
        new TabularButtonTracksterView({
            model   : options.model,
            $el     : this.$el
        });
    },

    expand_to_container: function(){
        if (this.$el.height() < this.scroll_elt.height()){
            this.attempt_to_fetch();
        }
    },

    attempt_to_fetch: function( func ){
        var self = this;
        if ( !this.loading_chunk && this.scrolled_to_bottom() ) {
            this.loading_chunk = true;
            this.loading_indicator.show();
            $.when(self.model.get_next_chunk()).then(function(result) {
                if (result) {
                    self._renderChunk(result);
                    self.loading_chunk = false;
                }
                self.loading_indicator.hide();
                self.expand_to_container();
            });
        }
    },

    render: function() {
        // Add loading indicator.
        this.loading_indicator = $('<div/>').attr('id', 'loading_indicator');
        this.$el.append(this.loading_indicator);

        // Add data table and header.
        var data_table = $('<table/>').attr({
            id: 'content_table',
            cellpadding: 0
        });
        this.$el.append(data_table);
        var column_names = this.model.get_metadata('column_names'),
            header_container = $('<thead/>').appendTo(data_table),
            header_row = $('<tr/>').appendTo(header_container);
        if (column_names) {
            header_row.append('<th>' + column_names.join('</th><th>') + '</th>');
        } else {
            for (var j = 1; j <= this.model.get_metadata('columns'); j++) {
                header_row.append('<th>' + j + '</th>');
            }
        }

        // Render first chunk.
        var self = this,
            first_chunk = this.model.get('first_data_chunk');
        if (first_chunk) {
            // First chunk is bootstrapped, so render now.
            this._renderChunk(first_chunk);
        }
        else {
            // No bootstrapping, so get first chunk and then render.
            $.when(self.model.get_next_chunk()).then(function(result) {
                self._renderChunk(result);
            });
        }

        // -- Show new chunks during scrolling. --

        // Set up chunk loading when scrolling using the scrolling element.
        this.scroll_elt.scroll(function(){
            self.attempt_to_fetch();
        });
    },

    /**
     * Returns true if user has scrolled to the bottom of the view.
     */
    scrolled_to_bottom: function() {
        return false;
    },

    // -- Helper functions. --

    _renderCell: function(cell_contents, index, colspan) {
        var $cell = $('<td>').text(cell_contents);
        var column_types = this.model.get_metadata('column_types');
        if (colspan !== undefined) {
            $cell.attr('colspan', colspan).addClass('stringalign');
        } else if (column_types) {
            if (index < column_types.length) {
                if (column_types[index] === 'str' || column_types[index] === 'list') {
                    /* Left align all str columns, right align the rest */
                    $cell.addClass('stringalign');
                }
            }
        }
        return $cell;
    },

    _renderRow: function(line) {
        // Check length of cells to ensure this is a complete row.
        var cells = line.split('\t'),
            row = $('<tr>'),
            num_columns = this.model.get_metadata('columns');

        if (this.row_count % 2 !== 0) {
            row.addClass('dark_row');
        }

        if (cells.length === num_columns) {
            _.each(cells, function(cell_contents, index) {
                row.append(this._renderCell(cell_contents, index));
            }, this);
        }
        else if (cells.length > num_columns) {
            // SAM file or like format with optional metadata included.
            _.each(cells.slice(0, num_columns - 1), function(cell_contents, index) {
                row.append(this._renderCell(cell_contents, index));
            }, this);
            row.append(this._renderCell(cells.slice(num_columns - 1).join('\t'), num_columns - 1));
        }
        else if (cells.length === 1){
            // Comment line, just return the one cell.
            row.append(this._renderCell(line, 0, num_columns));
        }
        else {
            // cells.length is greater than one, but less than num_columns.  Render cells and pad tds.
            // Possibly a SAM file or like format with optional metadata missing.
            // Could also be a tabular file with a line with missing columns.
            _.each(cells, function(cell_contents, index) {
                row.append(this._renderCell(cell_contents, index));
            }, this);
            _.each(_.range(num_columns - cells.length), function(){
                row.append($('<td>'));
            });
        }

        this.row_count++;
        return row;
    },

    _renderChunk: function(chunk) {
        var data_table = this.$el.find('table');
        _.each(chunk.ck_data.split('\n'), function(line, index) {
            if (line !== ''){
                data_table.append(this._renderRow(line));
            }
        }, this);
    }
});

/**
 * Tabular view that is placed at the top level of page. Scrolling occurs
 * view top-level elements outside of view.
 */
var TopLevelTabularDatasetChunkedView = TabularDatasetChunkedView.extend({

    initialize: function(options) {
        TabularDatasetChunkedView.prototype.initialize.call(this, options);

        // Scrolling happens in top-level elements.
        scroll_elt = _.find(this.$el.parents(), function(p) {
            return $(p).css('overflow') === 'auto';
        });

        // If no scrolling element found, use window.
        if (!scroll_elt) { scroll_elt = window; }

        // Wrap scrolling element for easy access.
        this.scroll_elt = $(scroll_elt);
    },

    /**
     * Returns true if user has scrolled to the bottom of the view.
     */
    scrolled_to_bottom: function() {
        return (this.$el.height() - this.scroll_elt.scrollTop() - this.scroll_elt.height() <= 0);
    }

});

/**
 * Tabular view tnat is embedded in a page. Scrolling occurs in view's el.
 */
var EmbeddedTabularDatasetChunkedView = TabularDatasetChunkedView.extend({

    initialize: function(options) {
        TabularDatasetChunkedView.prototype.initialize.call(this, options);

        // Because view is embedded, set up div to do scrolling.
        this.scroll_elt = this.$el.css({
            position: 'relative',
            overflow: 'scroll',
            height: options.height || '500px'
        });
    },

    /**
     * Returns true if user has scrolled to the bottom of the view.
     */
    scrolled_to_bottom: function() {
        return this.$el.scrollTop() + this.$el.innerHeight() >= this.el.scrollHeight;
    }

});

// button for trackster visualization
var TabularButtonTracksterView = Backbone.View.extend({

    // gene region columns
    col: {
        chrom   : null,
        start   : null,
        end     : null
    },

    // url for trackster
    url_viz     : null,

    // dataset id
    dataset_id  : null,

    // database key
    genome_build: null,

    // data type
    file_ext   : null,

    // backbone initialize
    initialize: function (options) {
        // check if environment is available
        var Galaxy = parent.Galaxy;

        // link galaxy modal or create one
        if (Galaxy && Galaxy.modal) {
            this.modal = Galaxy.modal;
        }

        // link galaxy frames
        if (Galaxy && Galaxy.frame) {
            this.frame = Galaxy.frame;
        }

        // check
        if (!this.modal || !this.frame) {
            return;
        }

        // model/metadata
        var model       = options.model;
        var metadata    = model.get('metadata');

        // check for datatype
        if (!model.get('file_ext')) {
            return;
        }

        // get data type
        this.file_ext = model.get('file_ext');

        // check for bed-file format
        if (this.file_ext == 'bed')
        {
            // verify that metadata exists
            if (metadata.get('chromCol') && metadata.get('startCol') && metadata.get('endCol'))
            {
                // read in columns
                this.col.chrom   = metadata.get('chromCol') - 1;
                this.col.start   = metadata.get('startCol') - 1;
                this.col.end     = metadata.get('endCol') - 1;
            } else {
                console.log('TabularButtonTrackster : Bed-file metadata incomplete.');
                return;
            }
        }

        // check for vcf-file format
        if (this.file_ext == 'vcf')
        {
            // search array
            function search (str, array) {
                for (var j = 0; j < array.length; j++)
                    if (array[j].match(str)) return j;
                return -1;
            };

            // load
            this.col.chrom = search('Chrom', metadata.get('column_names'));
            this.col.start = search('Pos', metadata.get('column_names'));
            this.col.end   = null;

            // verify that metadata exists
            if (this.col.chrom == -1 || this.col.start == -1) {
                console.log('TabularButtonTrackster : VCF-file metadata incomplete.');
                return;
            }
        }

        // check
        if(this.col.chrom === undefined) {
            return;
        }

        // get dataset id
        if (model.id) {
            this.dataset_id = model.id;
        } else {
            console.log('TabularButtonTrackster : Dataset identification is missing.');
            return;
        }

        // get url
        if (model.get('url_viz')) {
            this.url_viz = model.get('url_viz');
        } else {
            console.log('TabularButtonTrackster : Url for visualization controller is missing.');
            return;
        }

        // get genome_build / database key
        if (model.get('genome_build')) {
            this.genome_build = model.get('genome_build');
        }

        // create the icon
        var btn_viz = new mod_icon_btn.IconButtonView({
            model : new mod_icon_btn.IconButton({
                title       : 'Visualize',
                icon_class  : 'chart_curve',
                id          : 'btn_viz'
            })
        });

        // set element
        this.setElement(options.$el);

        // add to element
        this.$el.append(btn_viz.render().$el);

        // hide the button
        this.hide();
    },

    // backbone events
    events:
    {
        'mouseover tr'  : 'show',
        'mouseleave'    : 'hide'
    },

    // show button
    show: function (e) {
        // is numeric
        function is_numeric(n) {
            return !isNaN(parseFloat(n)) && isFinite(n);
        };

        // check
        if(this.col.chrom === null)
            return;

        // get selected data line
        var row = $(e.target).parent();

        // verify that location has been found
        var chrom = row.children().eq(this.col.chrom).html();
        var start = row.children().eq(this.col.start).html();

        // end is optional
        var end = this.col.end ? row.children().eq(this.col.end).html() : start;

        // double check location
        if (!chrom.match("^#") && chrom !== "" && is_numeric(start)) {

            // get target gene region
            var btn_viz_pars = {
                dataset_id  : this.dataset_id,
                gene_region : chrom + ":" + start + "-" + end
            };

            // get button position
            var offset  = row.offset();
            var left    = offset.left - 10;
            var top     = offset.top - $(window).scrollTop() + 3;

            // update css
            $('#btn_viz').css({'position': 'fixed', 'top': top + 'px', 'left': left + 'px'});
            $('#btn_viz').off('click');
            $('#btn_viz').click(this.create_trackster_action(this.url_viz, btn_viz_pars, this.genome_build));

            // show the button
            $('#btn_viz').show();
        } else {
            // hide the button
            $('#btn_viz').hide();
        }
    },

    // hide button
    hide: function () {
        this.$el.find('#btn_viz').hide();
    },

    // create action
    create_trackster_action : function (vis_url, dataset_params, dbkey) {
        // link this
        var self = this;

        // create function
        return function() {
            var listTracksParams = {};
            if (dbkey) {
                listTracksParams[ 'f-dbkey' ] = dbkey;
            }
            $.ajax({
                url: vis_url + '/list_tracks?' + $.param( listTracksParams ),
                dataType: 'html',
                error: function() {
                    // show error message
                    self.modal.show({
                        title   : 'Something went wrong!',
                        body    : 'Unfortunately we could not add this dataset to the track browser. Please try again or contact us.',
                        buttons : {
                            'Cancel': function(){
                                self.modal.hide();
                            }
                        }
                    });
                },
                success: function(table_html) {
                    self.modal.show({
                        title   : 'View Data in a New or Saved Visualization',
                        buttons :{
                            'Cancel': function(){
                                self.modal.hide();
                            },
                            'View in saved visualization': function(){
                                // show modal with saved visualizations
                                self.modal.show(
                                {
                                    title   : 'Add Data to Saved Visualization',
                                    body    : table_html,
                                    buttons : {
                                        'Cancel': function(){
                                            self.modal.hide();
                                        },
                                        'Add to visualization': function(){
                                            // hide
                                            self.modal.hide();

                                            // search selected fields
                                            self.modal.$el.find('input[name=id]:checked').each(function(){
                                                // get visualization id
                                                var vis_id = $(this).val();
                                                dataset_params.id = vis_id;

                                                // add widget
                                                self.frame.add({
                                                    title    : 'Trackster',
                                                    type     : 'url',
                                                    content  : vis_url + '/trackster?' + $.param(dataset_params)
                                                });
                                            });
                                        }
                                    }
                                });
                            },
                            'View in new visualization': function(){
                                // hide
                                self.modal.hide();

                                // add widget
                                self.frame.add({
                                    title    : 'Trackster',
                                    type     : 'url',
                                    content  : vis_url + '/trackster?' + $.param(dataset_params)
                                });
                            }
                        }
                    });
                }
            });
            return false;
        };
    }
});

// -- Utility functions. --

/**
 * Create a model, attach it to a view, render view, and attach it to a parent element.
 */
var createModelAndView = function(model, view, model_config, parent_elt) {
    // Create model, view.
    var a_view = new view({
        model: new model(model_config)
    });

    // Render view and add to parent element.
    a_view.render();
    if (parent_elt) {
        parent_elt.append(a_view.$el);
    }

    return a_view;
};

/**
 * Create a tabular dataset chunked view (and requisite tabular dataset model)
 * and appends to parent_elt.
 */
var createTabularDatasetChunkedView = function(options) {
    // If no model, create and set model from dataset config.
    if (!options.model) {
        options.model = new TabularDataset(options.dataset_config);
    }

    var parent_elt = options.parent_elt;
    var embedded = options.embedded;

    // Clean up options so that only needed options are passed to view.
    delete options.embedded;
    delete options.parent_elt;
    delete options.dataset_config;

    // Create and set up view.
    var view = (embedded ? new EmbeddedTabularDatasetChunkedView(options) :
                           new TopLevelTabularDatasetChunkedView(options));
    view.render();

    if (parent_elt) {
        parent_elt.append(view.$el);
        // If we're sticking this in another element, once it's appended check
        // to make sure we've filled enough space.
        // Without this, the scroll elements don't work.
        view.expand_to_container();
    }

    return view;
};

return {
    Dataset: Dataset,
    TabularDataset: TabularDataset,
    DatasetCollection: DatasetCollection,
    TabularDatasetChunkedView: TabularDatasetChunkedView,
    createTabularDatasetChunkedView: createTabularDatasetChunkedView
};

});
