define( ["viz/visualization", "libs/bbi/bigwig"],
        function(visualization, bigwig) {

    /**
     * Data manager for BBI datasets/files, including BigWig and BigBed.
     */
    var BBIDataManager = visualization.GenomeDataManager.extend({

        /**
         * Load data from server and manages data entries. Adds a Deferred to manager
         * for region; when data becomes available, replaces Deferred with data.
         * Returns the Deferred that resolves when data is available.
         */
        load_data: function(region, mode, resolution, extra_params) {
            var deferred = $.Deferred();
            this.set_data(region, deferred);

            var url = galaxy_config.root + 'datasets/' + this.get('dataset').id + '/display',
                self = this;
                var promise = new $.Deferred();
                $.when(bigwig.makeBwg(url)).then(function(bb, err) {
                    $.when(bb.readWigData(region.get("chrom"), region.get("start"), region.get("end"))).then(function(data) {
                    // Transform data into "bigwig" format. "bigwig" format is an array of 2-element arrays
                    // where each array is [position, score].
                    var result = [];
                    data.forEach(function(d) {
                        // Each data element includes a min and max. If min and max are the same,
                        // then entry is single base-pair resolution and only a single data point
                        // is added. Otherwise entry is multiple base pairs and two data points are
                        // added, one for the start and one for the end.

                        // Add data point for entry start.
                        result.push([d.min, d.score]);

                        if (d.min !== d.max) {
                            // Multi base-pair entry, so two data points are generated.
                            result.push([d.max, d.score]);
                        }
                    });

                    var entry = {
                            data: result,
                            region: region,
                            dataset_type: 'bigwig'
                        };

                    self.set_data(region, entry);
                    deferred.resolve(entry);
                });
            });

            return deferred;
        },
    });

    return {
        BBIDataManager: BBIDataManager
    };

});
