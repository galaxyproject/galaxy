import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import visualization from "viz/visualization";
import * as bigwig from "libs/bbi/bigwig";

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

        var url = `${getAppRoot()}datasets/${this.get("dataset").id}/display`;

        var self = this;
        $.when(bigwig.makeBwg(url)).then((bb, err) => {
            $.when(bb.readWigData(region.get("chrom"), region.get("start"), region.get("end"))).then(data => {
                // Transform data into "bigwig" format for LinePainter. "bigwig" format is an array of 2-element arrays
                // where each element is [position, score]; unlike real bigwig format, no gaps are allowed.
                var result = [];

                var prev = { max: Number.MIN_VALUE };
                data.forEach(d => {
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
                    dataset_type: "bigwig"
                };

                self.set_data(region, entry);
                deferred.resolve(entry);
            });
        });

        return deferred;
    }
});

export default {
    BBIDataManager: BBIDataManager
};
