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
            $.when(bigwig.makeBwg(url)).then(function(bb, err) {
                var start_promise = new $.Deferred(),
                    promise = start_promise;
                if ( bb.zoomLevels.length > 0 ) {
                    for (var i=bb.zoomLevels.length - 1; i >= -1; i--){
                        promise = self.check_zoom_data(bb, region, i, promise);
                    }
                }
                else {
                    promise = self.check_zoom_data(bb, region, -1, promise);
                }
                $.when(promise).then(function(result) {
                    var entry = {
                            data: result,
                            region: region,
                            dataset_type: 'bigwig'
                        };
                    self.set_data(region, entry);
                    deferred.resolve(entry);
                });
                // Start zoom level promise chain
                start_promise.resolve([]);
            });

            return deferred;
        },

        check_zoom_data: function(bb, region, zoom, prev_promise) {
            var promise = new $.Deferred(),
                MIN_DATA_POINTS = 10000;
            // Wait until previous zoom level promise if fulfilled
            $.when( prev_promise ).then( function( pdata ) {
                // Check if previous level found acceptable data
                if ( pdata.length > 0 ) {
                    // If so, pass it on
                    promise.resolve(pdata);
                }
                else {
                    // Otherwise, call function for current zoom level and check data
                    $.when(bb.readWigData(region.get("chrom"), region.get("start"), region.get("end"), zoom)).then(function(data) {
                        // check if the data density is sufficiently high or at unzoomed level
                        if ( zoom == -1 || data.length > MIN_DATA_POINTS ){
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
                            // Return data
                            promise.resolve(result);
                        }
                        else {
                            // If density is too low, pass empty array so next level 
                            promise.resolve([]);
                        }
                    });
                }
            });
            return promise
        },
    });

    return {
        BBIDataManager: BBIDataManager
    };

});
