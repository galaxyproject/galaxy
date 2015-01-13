define( ["libs/underscore"], function( _ ) {

var extend = _.extend;

// HACK: LABEL_SPACING is currently duplicated between here and painters
var LABEL_SPACING = 2,
    PACK_SPACING = 5;

/**
 * Hold slotting information for a feature.
 */
var SlottedInfo = function(slot, feature) {
    this.slot = slot;
    this.feature = feature;
};

/**
 * FeatureSlotter determines slots in which to draw features for vertical
 * packing.
 *
 * This implementation is incremental, any feature assigned a slot will be
 * retained for slotting future features.
 */
var FeatureSlotter = function (w_scale, mode, max_rows, measureText) {
    this.slots = {};
    this.start_end_dct = {};
    this.w_scale = w_scale;
    this.mode = mode;
    this.include_label = (mode === "Pack");
    this.max_rows = max_rows;
    this.measureText = measureText;
};

/**
 * Slot a set of features, `this.slots` will be updated with slots by id, and
 * the largest slot required for the passed set of features is returned
 */
extend( FeatureSlotter.prototype, {
    /**
     * Get drawing coordinate for a feature.
     */
    _get_draw_coords: function(feature) {
        // Get initial draw coordinates using w_scale.
        var draw_start = Math.floor(feature[1] * this.w_scale),
            draw_end = Math.ceil(feature[2] * this.w_scale),
            f_name = feature[3],
            text_align;

        // Update start, end drawing locations to include feature name.
        // Try to put the name on the left, if not, put on right.
        if (f_name !== undefined && this.include_label ) {
            // Add gap for label spacing and extra pack space padding
            // TODO: Fix constants
            var text_len = this.measureText(f_name).width + (LABEL_SPACING + PACK_SPACING);
            if (draw_start - text_len >= 0) {
                draw_start -= text_len;
                text_align = "left";
            } else {
                draw_end += text_len;
                text_align = "right";
            }
        }

        /*
        if (slot_num < 0) {
            
            TODO: this is not yet working --
            console.log(feature_uid, "looking for slot with text on the right");
            // Slot not found. If text was on left, try on right and see
            // if slot can be found.
            // TODO: are there any checks we need to do to ensure that text
            // will fit on tile?
            if (text_align === "left") {
                draw_start -= text_len;
                draw_end -= text_len;
                text_align = "right";
                slot_num = find_slot(draw_start, draw_end);
            }
            if (slot_num >= 0) {
                console.log(feature_uid, "found slot with text on the right");
            }

        }
        */

        return [draw_start, draw_end];
    },

    /**
     * Find the first slot such that current feature doesn't overlap any other features in that slot.
     * Returns -1 if no slot was found.
     */
    _find_slot: function(draw_coords) {
        // TODO: Use a data structure for faster searching of available slots.
        var draw_start = draw_coords[0],
            draw_end = draw_coords[1];
        for (var slot_num = 0; slot_num <= this.max_rows; slot_num++) {
            var has_overlap = false,
                slot = this.start_end_dct[slot_num];
            if (slot !== undefined) {
                // Iterate through features already in slot to see if current feature will fit.
                for (var k = 0, k_len = slot.length; k < k_len; k++) {
                    var s_e = slot[k];
                    if (draw_end > s_e[0] && draw_start < s_e[1]) {
                        // There is overlap
                        has_overlap = true;
                        break;
                    }
                }
            }
            if (!has_overlap) {
                return slot_num;
            }
        }
        return -1;
    },

    /**
     * Slot features.
     */
    slot_features: function( features ) {
        var start_end_dct = this.start_end_dct,
            undone = [], 
            highest_slot = 0,
            feature,
            feature_uid;

        // Loop through features to (a) find those that are not yet slotted and (b) update
        // those that are slotted if new information is availabe. For (a), features already
        // slotted (based on slotting from other tiles) will retain their current slot.
        for (var i = 0, len = features.length; i < len; i++) {
            feature = features[i];
            feature_uid = feature[0];
            var slotted_info = this.slots[feature_uid];

            // Separate and handle slotted vs. unslotted features.
            if (slotted_info) {
                // Feature is slotted; if feature now has larger start/end coordinates,
                // update drawing coordinates.
                if (feature[1] < slotted_info.feature[1]  || slotted_info.feature[2] < feature[2]) {
                    // Feature has changed (e.g. a single read now has its pair), so recalculate its 
                    // drawing coordinates.
                    var old_draw_coords = this._get_draw_coords(slotted_info.feature),
                        new_draw_coords = this._get_draw_coords(feature),
                        slotted_coords = this.start_end_dct[slotted_info.slot];
                    for (var k = 0; k < slotted_coords.length; k++) {
                        var dc = slotted_coords[k];
                        if (dc[0] === old_draw_coords[0] && dc[1] === old_draw_coords[1]) {
                            // Replace old drawing coordinates with new ones.
                            slotted_coords[k] = new_draw_coords;
                        }
                    }
                }
                highest_slot = Math.max(highest_slot, this.slots[feature_uid].slot);
            } 
            else {
                undone.push(i);
            }
        }
        
        // Slot unslotted features.
        
        // Do slotting.
        for (var i = 0, len = undone.length; i < len; i++) {
            feature = features[undone[i]];
            feature_uid = feature[0];
            var draw_coords = this._get_draw_coords(feature);
                        
            // Find slot.
            var slot_num = this._find_slot(draw_coords);

            // Do slotting.
            if (slot_num >= 0) {
                // Add current feature to slot.
                if (start_end_dct[slot_num] === undefined) {
                    start_end_dct[slot_num] = [];
                }
                start_end_dct[slot_num].push(draw_coords);
                this.slots[feature_uid] = new SlottedInfo(slot_num, feature);
                highest_slot = Math.max(highest_slot, slot_num);
            }
        }
        
        // Debugging: view slots data.
        /*
        for (var i = 0; i < MAX_FEATURE_DEPTH; i++) {
            var slot = start_end_dct[i];
            if (slot !== undefined) {
                console.log(i, "*************");
                for (var k = 0, k_len = slot.length; k < k_len; k++) {
                    console.log("\t", slot[k][0], slot[k][1]);
                }
            }
        }
        */
        return highest_slot + 1;
    }
});

return {
    FeatureSlotter: FeatureSlotter
};

});
