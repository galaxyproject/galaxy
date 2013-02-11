// Additional dependencies: jQuery, underscore.
define(["libs/backbone/backbone-relational"], function() {

/**
 * Dataset metedata.
 */
var DatasetMetadata = Backbone.RelationalModel.extend({});

/**
 * A dataset. In Galaxy, datasets are associated with a history, so
 * this object is also known as a HistoryDatasetAssociation.
 */
var Dataset = Backbone.RelationalModel.extend({
    defaults: {
        id: '',
        type: '',
        name: '',
        hda_ldda: 'hda',
        metadata: null
    },

    initialize: function() {
        // -- Create and initialize metadata. -- 

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

        this.set('metadata', metadata);
    },

    /**
     * Returns dataset metadata for a given attribute.
     */
    get_metadata: function(attribute) {
        return this.attributes.metadata.get(attribute);
    },

    urlRoot: galaxy_paths.get('datasets_url')
});

/**
 * A tabular dataset. This object extends dataset to provide incremental chunked data.
 */
var TabularDataset = Dataset.extend({
    defaults: _.extend({}, Dataset.prototype.defaults, {
        chunk_url: null,
        first_data_chunk: null,
        chunk_index: -1,
        at_eof: false
    }),

    initialize: function(options) {
        Dataset.prototype.initialize.call(this);

        // If first data chunk is available, next chunk is 1.
        this.attributes.chunk_index = (this.attributes.first_data_chunk ? 1 : 0);
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
            chunk: self.attributes.chunk_index++
        }).success(function(chunk) {
            var rval;
            if (chunk.ck_data !== '') {
                // Found chunk.
                rval = chunk;
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
 * Provides table-based, dynamic view of a tabular dataset.
 */
var TabularDatasetChunkedView = Backbone.View.extend({

    initialize: function(options) {},

    render: function() {
        // Add loading indicator div.
        this.$el.append( $('<div/>').attr('id', 'loading_indicator') );

        // Add data table and header.
        var data_table = $('<table/>').attr({
            id: 'content_table',
            cellpadding: 0
        });
        this.$el.append(data_table);
        var column_names = this.model.get_metadata('column_names');
        if (column_names) {
            data_table.append('<tr><th>' + column_names.join('</th><th>') + '</th></tr>');
        }

        // Add first chunk.
        var first_chunk = this.model.get('first_data_chunk');
        if (first_chunk) {
            this._renderChunk(first_chunk);
        }

        // Show new chunks during scrolling.
        var self = this;
        $(window).scroll(function() {
            if ($(window).scrollTop() === $(document).height() - $(window).height()) {
                $.when(self.model.get_next_chunk()).then(function(result) {
                    if (result) {
                        self._renderChunk(result);
                    }
                });
            }
        });
        $('#loading_indicator').ajaxStart(function(){
           $(this).show();
        }).ajaxStop(function(){
           $(this).hide();
        });
    },

    // -- Helper functions. --

    _renderCell: function(cell_contents, index, colspan) {
        var column_types = this.model.get_metadata('column_types');
        if (colspan !== undefined) {
            return $('<td>').attr('colspan', colspan).addClass('stringalign').text(cell_contents);
        }
        else if (column_types[index] === 'str' || column_types === 'list') {
            /* Left align all str columns, right align the rest */
            return $('<td>').addClass('stringalign').text(cell_contents);
        }
        else {
            return $('<td>').text(cell_contents);
        }
    },

    _renderRow: function(line) {
        // Check length of cells to ensure this is a complete row.
        var cells = line.split('\t'),
            row = $('<tr>'),
            num_columns = this.model.get_metadata('columns');
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
        else if (num_columns > 5 && cells.length === num_columns - 1 ) {
            // SAM file or like format with optional metadata missing.
            _.each(cells, function(cell_contents, index) {
                row.append(this._renderCell(cell_contents, index));
            }, this);
            row.append($('<td>'));
        }
        else {
            // Comment line, just return the one cell.
            row.append(this._renderCell(line, 0, num_columns));
        }
        return row;
    },

    _renderChunk: function(chunk) {
        var data_table = this.$el.find('table');
        _.each(chunk.ck_data.split('\n'), function(line, index) {
            data_table.append(this._renderRow(line));
        }, this);
    }
});

return {
	Dataset: Dataset,
    TabularDataset: TabularDataset,
	DatasetCollection: DatasetCollection,
    TabularDatasetChunkedView: TabularDatasetChunkedView
};

});
