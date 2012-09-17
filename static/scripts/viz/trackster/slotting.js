define( ["libs/underscore"], function( _ ) {

var extend = _.extend;

// HACK: LABEL_SPACING is currently duplicated between here and painters
var LABEL_SPACING = 2,
    PACK_SPACING = 5;

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
    slot_features: function( features ) {
        var w_scale = this.w_scale, 
            start_end_dct = this.start_end_dct,
            undone = [], 
            slotted = [], 
            highest_slot = 0, 
            max_rows = this.max_rows;
        
        // If feature already exists in slots (from previously seen tiles), use the same slot,
        // otherwise if not seen, add to "undone" list for slot calculation.
    
        // TODO: Should calculate zoom tile index, which will improve performance
        // by only having to look at a smaller subset
        // if (this.start_end_dct[0] === undefined) { this.start_end_dct[0] = []; }
        for (var i = 0, len = features.length; i < len; i++) {
            var feature = features[i],
                feature_uid = feature[0];
            if (this.slots[feature_uid] !== undefined) {
                highest_slot = Math.max(highest_slot, this.slots[feature_uid]);
                slotted.push(this.slots[feature_uid]);
            } else {
                undone.push(i);
            }
        }
                
        // Slot unslotted features.
        
        // Find the first slot such that current feature doesn't overlap any other features in that slot.
        // Returns -1 if no slot was found.
        var find_slot = function(f_start, f_end) {
            // TODO: Fix constants
            for (var slot_num = 0; slot_num <= max_rows; slot_num++) {
                var has_overlap = false,
                    slot = start_end_dct[slot_num];
                if (slot !== undefined) {
                    // Iterate through features already in slot to see if current feature will fit.
                    for (var k = 0, k_len = slot.length; k < k_len; k++) {
                        var s_e = slot[k];
                        if (f_end > s_e[0] && f_start < s_e[1]) {
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
        };
        
        // Do slotting.
        for (var i = 0, len = undone.length; i < len; i++) {
            var feature = features[undone[i]],
                feature_uid = feature[0],
                feature_start = feature[1],
                feature_end = feature[2],
                feature_name = feature[3],
                // Where to start, end drawing on screen.
                f_start = Math.floor( feature_start * w_scale ),
                f_end = Math.ceil( feature_end * w_scale ),
                text_len = this.measureText(feature_name).width,
                text_align;
            
            // Update start, end drawing locations to include feature name.
            // Try to put the name on the left, if not, put on right.
            if (feature_name !== undefined && this.include_label ) {
                // Add gap for label spacing and extra pack space padding
                // TODO: Fix constants
                text_len += (LABEL_SPACING + PACK_SPACING);
                if (f_start - text_len >= 0) {
                    f_start -= text_len;
                    text_align = "left";
                } else {
                    f_end += text_len;
                    text_align = "right";
                }
            }
                        
            // Find slot.
            var slot_num = find_slot(f_start, f_end);

            /*
            if (slot_num < 0) {
                
                TODO: this is not yet working --
                console.log(feature_uid, "looking for slot with text on the right");
                // Slot not found. If text was on left, try on right and see
                // if slot can be found.
                // TODO: are there any checks we need to do to ensure that text
                // will fit on tile?
                if (text_align === "left") {
                    f_start -= text_len;
                    f_end -= text_len;
                    text_align = "right";
                    slot_num = find_slot(f_start, f_end);
                }
                if (slot_num >= 0) {
                    console.log(feature_uid, "found slot with text on the right");
                }
    
            }
            */
            // Do slotting.
            if (slot_num >= 0) {
                // Add current feature to slot.
                if (start_end_dct[slot_num] === undefined) {
                    start_end_dct[slot_num] = [];
                }
                start_end_dct[slot_num].push([f_start, f_end]);
                this.slots[feature_uid] = slot_num;
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
