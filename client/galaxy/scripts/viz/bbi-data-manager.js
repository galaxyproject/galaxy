define( ["viz/visualization", "libs/bbi/bigwig"],
        function(visualization, bigwig) {

    /**
     * Data manager for BBI datasets/files, including BigWig and BigBed.
     */
    var BBIDataManager = visualization.GenomeDataManager.extend({
        /**
         * Load data from server and manage data entries. Adds a Deferred to manager
         * for region; when data becomes available, replaces Deferred with data.
         * Returns the Deferred that resolves when data is available.
         */
        load_data: function(region, mode, resolution, extra_params) {
            var deferred = $.Deferred();
            this.set_data(region, deferred);

            var url = Galaxy.root + 'datasets/' + this.get('dataset').id + '/display',
                self = this;
                var promise = new $.Deferred();
                $.when(bigwig.makeBwg(url)).then(function(bb, err) {
                    self.load_zoom_data(bb, region, deferred);
            });

            return deferred;
        },

        load_zoom_data: function(bb, region, deferred){
            var self = this,
                MIN_DATA_POINTS = 15000;

            $.when(bb.readWigData(region.get("chrom"), region.get("start"), region.get("end"))).then(function(data) {
                // Check if the zoom levels exist, if we're at max zoom out, or data density is too low
                if ( bb.zoom == -1 || data.length > MIN_DATA_POINTS) {
                    // Transform data into "bigwig" format for LinePainter. "bigwig" format is an array of 2-element arrays
                    // where each element is [position, score]; unlike real bigwig format, no gaps are allowed.
                    var result = [],
                        prev = { max: Number.MIN_VALUE };
                    data.forEach(function(d) {
                        // If there is a gap between prev and d, fill it with an interval with score 0.
                        // This is necessary for LinePainter to draw correctly.
                        if (prev.max !== d.min - 1) {
                            // +1 to start after previous region.
                            result.push([prev.max + 1, 0]);
                            // -2 = -1 for converting from 1-based to 0-based coordinates,
                            //      -1 for ending before current region.
                            result.push([d.min - 2, 0]);
                        }

                        // Add data point for entry start. -1 to convert from wiggle
                        // 1-based coordinates to 0-based browser coordinates.
                        result.push([d.min - 1, d.score]);

                        // Add data point for entry end:
                        result.push([d.max, d.score]);

                        prev = d;
                    });

                    var entry = {
                            data: result,
                            region: region,
                            dataset_type: 'bigwig'
                        };
                    self.set_data(region, entry);
                    deferred.resolve(entry);
                }
                else {
                    self.load_zoom_data(bb, region, deferred);
                }
            });
        },
    });

    return {
        BBIDataManager: BBIDataManager
    };

});
