define( ["libs/underscore"], function( _ ) {

var extend = _.extend;

/**
 * Compute the type of overlap between two regions. They are assumed to be on the same chrom/contig.
 * The overlap is computed relative to the second region; hence, OVERLAP_START indicates that the first
 * region overlaps the start (but not the end) of the second region.
 * NOTE: Coordinates are assumed to be in BED format: half open (start is closed, end is open).
 */
var BEFORE = 1001, CONTAINS = 1002, OVERLAP_START = 1003, OVERLAP_END = 1004, CONTAINED_BY = 1005, AFTER = 1006;
var compute_overlap = function(first_region, second_region) {
    var 
        first_start = first_region[0], first_end = first_region[1],
        second_start = second_region[0], second_end = second_region[1],
        overlap;
    if (first_start < second_start) {
        if (first_end <= second_start) {
            overlap = BEFORE;
        }
        else if (first_end <= second_end) {
            overlap = OVERLAP_START;
        }
        else { // first_end > second_end
            overlap = CONTAINS;
        }
    }
    else { // first_start >= second_start
        if (first_start > second_end) {
            overlap = AFTER;
        }
        else if (first_end <= second_end) {
            overlap = CONTAINED_BY;
        }
        else {
            overlap = OVERLAP_END;
        }
    }
    
    return overlap;
};

/**
 * Returns true if regions overlap.
 */
var is_overlap = function(first_region, second_region) {
    var overlap = compute_overlap(first_region, second_region);
    return (overlap !== BEFORE && overlap !== AFTER);
};

/**
 * Draw a dashed line on a canvas using filled rectangles. This function is based on:
 * http://vetruvet.blogspot.com/2010/10/drawing-dashed-lines-on-html5-canvas.html
 * However, that approach uses lines, which don't seem to render as well, so use
 * rectangles instead.
 */
var dashedLine = function(ctx, x1, y1, x2, y2, dashLen) {
    if (dashLen === undefined) { dashLen = 4; }
    var dX = x2 - x1;
    var dY = y2 - y1;
    var dashes = Math.floor(Math.sqrt(dX * dX + dY * dY) / dashLen);
    var dashX = dX / dashes;
    var dashY = dY / dashes;
    var q;
    
    for (q = 0; q < dashes; q++, x1 += dashX, y1 += dashY) {
        if (q % 2 !== 0) {
            continue;
        }
        ctx.fillRect(x1, y1, dashLen, 1);
    }
};

/**
 * Draw an isosceles triangle that points down.
 */
var drawDownwardEquilateralTriangle = function(ctx, down_vertex_x, down_vertex_y, side_len) {
    // Compute other two points of triangle.
    var 
        x1 = down_vertex_x - side_len/2,
        x2 = down_vertex_x + side_len/2,
        y = down_vertex_y - Math.sqrt( side_len*3/2 );
        
    // Draw and fill.
    ctx.beginPath();
    ctx.moveTo(x1, y);
    ctx.lineTo(x2, y);
    ctx.lineTo(down_vertex_x, down_vertex_y);
    ctx.lineTo(x1, y);

    ctx.strokeStyle = this.fillStyle;
    ctx.fill();
    ctx.stroke();
    ctx.closePath();
};

/**
 * Base class for all scalers. Scalers produce values that are used to change (scale) drawing attributes.
 */
var Scaler = function(default_val) {
    this.default_val = (default_val ? default_val : 1);
};

/**
 * Produce a scaling value.
 */
Scaler.prototype.gen_val = function(input) {
    return this.default_val;
};

/**
 * Base class for painters
 *
 * -- Mode and prefs are both optional
 */
var Painter = function(data, view_start, view_end, prefs, mode) {
    // Data and data properties
    this.data = data;
    // View
    this.view_start = view_start;
    this.view_end = view_end;
    // Drawing prefs
    this.prefs = extend( {}, this.default_prefs, prefs );
    this.mode = mode;
};

Painter.prototype.default_prefs = {};

/**
 * Draw on the context using a rectangle of width x height. w_scale is 
 * needed because it cannot be computed from width and view size alone
 * as a left_offset may be present.
 */
Painter.prototype.draw = function(ctx, width, height, w_scale) {};

/**
 * SummaryTreePainter, a histogram showing number of intervals in a region
 */
var SummaryTreePainter = function(data, view_start, view_end, prefs, mode) {
    Painter.call(this, data, view_start, view_end, prefs, mode);
};

SummaryTreePainter.prototype.default_prefs = { show_counts: false };

SummaryTreePainter.prototype.draw = function(ctx, width, height, w_scale) {
    var view_start = this.view_start,
        points = this.data.data,
        max = (this.prefs.histogram_max ? this.prefs.histogram_max : this.data.max),
        // Set base Y so that max label and data do not overlap. Base Y is where rectangle bases
        // start. However, height of each rectangle is relative to required_height; hence, the
        // max rectangle is required_height.
        base_y = height;
        delta_x_px = Math.ceil(this.data.delta * w_scale);
    ctx.save();
    
    for (var i = 0, len = points.length; i < len; i++) {
        var x = Math.floor( (points[i][0] - view_start) * w_scale );
        var y = points[i][1];
        
        if (!y) { continue; }
        var y_px = y / max * height;
        if (y !== 0 && y_px < 1) { y_px = 1; }

        ctx.fillStyle = this.prefs.block_color;
        ctx.fillRect( x, base_y - y_px, delta_x_px, y_px );
        
        // Draw number count if it can fit the number with some padding, otherwise things clump up
        var text_padding_req_x = 4;
        if (this.prefs.show_counts && (ctx.measureText(y).width + text_padding_req_x) < delta_x_px) {
            ctx.fillStyle = this.prefs.label_color;
            ctx.textAlign = "center";
            ctx.fillText(y, x + (delta_x_px/2), 10);
        }
    }
    
    ctx.restore();
};

var LinePainter = function(data, view_start, view_end, prefs, mode) {
    Painter.call( this, data, view_start, view_end, prefs, mode );
    var i, len;
    if ( this.prefs.min_value === undefined ) {
        var min_value = Infinity;
        for (i = 0, len = this.data.length; i < len; i++) {
            min_value = Math.min( min_value, this.data[i][1] );
        }
        this.prefs.min_value = min_value;
    }
    if ( this.prefs.max_value === undefined ) {
        var max_value = -Infinity;
        for (i = 0, len = this.data.length; i < len; i++) {
            max_value = Math.max( max_value, this.data[i][1] );
        }
        this.prefs.max_value = max_value;
    }
};

LinePainter.prototype.default_prefs = { min_value: undefined, max_value: undefined, mode: "Histogram", color: "#000", overflow_color: "#F66" };

LinePainter.prototype.draw = function(ctx, width, height, w_scale) {
    var in_path = false,
        min_value = this.prefs.min_value,
        max_value = this.prefs.max_value,
        vertical_range = max_value - min_value,
        height_px = height,
        view_start = this.view_start,
        mode = this.mode,
        data = this.data;

    ctx.save();

    // Pixel position of 0 on the y axis
    var y_zero = Math.round( height + min_value / vertical_range * height );

    // Horizontal line to denote x-axis
    if ( mode !== "Intensity" ) {
        ctx.fillStyle = "#aaa";
        ctx.fillRect( 0, y_zero, width, 1 );
    }
    
    ctx.beginPath();
    var x_scaled, y, delta_x_px;
    if (data.length > 1) {
        delta_x_px = Math.ceil((data[1][0] - data[0][0]) * w_scale);
    } 
    else {
        delta_x_px = 10;
    }
    
    // Extract RGB from preference color.
    var pref_color = parseInt( this.prefs.color.slice(1), 16 ),
        pref_r = (pref_color & 0xff0000) >> 16,
        pref_g = (pref_color & 0x00ff00) >> 8,
        pref_b = pref_color & 0x0000ff;
    
    // Paint track.
    for (var i = 0, len = data.length; i < len; i++) {
        ctx.fillStyle = ctx.strokeStyle = this.prefs.color;
        // -0.5 to offset drawing between bases.
        x_scaled = Math.round((data[i][0] - view_start - 0.5) * w_scale);
        y = data[i][1];
        var top_overflow = false, bot_overflow = false;
        if (y === null) {
            if (in_path && mode === "Filled") {
                ctx.lineTo(x_scaled, height_px);
            }
            in_path = false;
            continue;
        }
        if (y < min_value) {
            bot_overflow = true;
            y = min_value;
        } else if (y > max_value) {
            top_overflow = true;
            y = max_value;
        }
    
        if (mode === "Histogram") {
            // y becomes the bar height in pixels, which is the negated for canvas coords
            y = Math.round( y / vertical_range * height_px );
            ctx.fillRect(x_scaled, y_zero, delta_x_px, - y );
        } 
        else if (mode === "Intensity") {
            var 
                saturation = (y - min_value) / vertical_range,
                // Range is [pref_color, 255] where saturation = 0 --> 255 and saturation = 1 --> pref color
                new_r = Math.round( pref_r + (255 - pref_r) * (1 - saturation) ),
                new_g = Math.round( pref_g + (255 - pref_g) * (1 - saturation) ),
                new_b = Math.round( pref_b + (255 - pref_b) * (1 - saturation) );
            ctx.fillStyle = "rgb(" + new_r + "," + new_g + "," + new_b + ")";
            ctx.fillRect(x_scaled, 0, delta_x_px, height_px);
        } 
        else {
            // console.log(y, track.min_value, track.vertical_range, (y - track.min_value) / track.vertical_range * track.height_px);
            y = Math.round( height_px - (y - min_value) / vertical_range * height_px );
            // console.log(canvas.get(0).height, canvas.get(0).width);
            if (in_path) {
                ctx.lineTo(x_scaled, y);
            } 
            else {
                in_path = true;
                if (mode === "Filled") {
                    ctx.moveTo(x_scaled, height_px);
                    ctx.lineTo(x_scaled, y);
                } 
                else {
                    ctx.moveTo(x_scaled, y);
                }
            }
        }
        // Draw lines at boundaries if overflowing min or max
        ctx.fillStyle = this.prefs.overflow_color;
        if (top_overflow || bot_overflow) {
            var overflow_x;
            if (mode === "Histogram" || mode === "Intensity") {
                overflow_x = delta_x_px;
            } 
            else { // Line and Filled, which are points
                x_scaled -= 2; // Move it over to the left so it's centered on the point
                overflow_x = 4;
            }
            if (top_overflow) {
                ctx.fillRect(x_scaled, 0, overflow_x, 3);
            }
            if (bot_overflow) {
                ctx.fillRect(x_scaled, height_px - 3, overflow_x, 3);
            }
        }
        ctx.fillStyle = this.prefs.color;
    }
    if (mode === "Filled") {
        if (in_path) {
            ctx.lineTo( x_scaled, y_zero );
            ctx.lineTo( 0, y_zero );
        }
        ctx.fill();
    } 
    else {
        ctx.stroke();
    }
    
    ctx.restore();
};

/**
 * Mapper that contains information about feature locations and data.
 */
var FeaturePositionMapper = function(slot_height) {
    this.feature_positions = {};
    this.slot_height = slot_height;
    this.translation = 0;
    this.y_translation = 0;
};

/**
 * Map feature data to a position defined by <slot, x_start, x_end>.
 */
FeaturePositionMapper.prototype.map_feature_data = function(feature_data, slot, x_start, x_end) {
    if (!this.feature_positions[slot]) {
        this.feature_positions[slot] = [];
    }
    this.feature_positions[slot].push({
        data: feature_data,
        x_start: x_start,
        x_end: x_end
    });
};

/**
 * Get feature data for position <x, y>
 */
FeaturePositionMapper.prototype.get_feature_data = function(x, y) {
    // Find slot using Y.
    var slot = Math.floor( (y-this.y_translation)/this.slot_height ),
        feature_dict;

    // May not be over a slot due to padding, margin, etc.
    if (!this.feature_positions[slot]) {
        return null;
    }
    
    // Find feature using X.
    x += this.translation;
    for (var i = 0; i < this.feature_positions[slot].length; i++) {
        feature_dict = this.feature_positions[slot][i];
        if (x >= feature_dict.x_start && x <= feature_dict.x_end) {
            return feature_dict.data;
        }
    }
};

/**
 * Abstract object for painting feature tracks. Subclasses must implement draw_element() for painting to work.
 * Painter uses a 0-based, half-open coordinate system; start coordinate is closed--included--and the end is open.
 * This coordinate system matches the BED format.
 */
var FeaturePainter = function(data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler) {
    Painter.call(this, data, view_start, view_end, prefs, mode);
    this.alpha_scaler = (alpha_scaler ? alpha_scaler : new Scaler());
    this.height_scaler = (height_scaler ? height_scaler : new Scaler());
};

FeaturePainter.prototype.default_prefs = { block_color: "#FFF", connector_color: "#FFF" };

extend(FeaturePainter.prototype, {
    get_required_height: function(rows_required, width) {
        // y_scale is the height per row
        var required_height = this.get_row_height(),
            y_scale = required_height,
            mode = this.mode;
        // If using a packing mode, need to multiply by the number of slots used
        if (mode === "no_detail" || mode === "Squish" || mode === "Pack") {
            required_height = rows_required * y_scale;
        }
        return required_height + this.get_top_padding(width) + this.get_bottom_padding(width);
    },
    /** Extra padding before first row of features */
    get_top_padding: function(width) {
        return 0;
    },
    /** Extra padding after last row of features */
    get_bottom_padding: function(width) {
        // Pad bottom by half a row, at least 5 px
        return Math.max( Math.round( this.get_row_height() / 2 ), 5 );
    },
    /**
     * Draw data on ctx using slots and within the rectangle defined by width and height. Returns
     * a FeaturePositionMapper object with information about where features were drawn.
     */
    draw: function(ctx, width, height, w_scale, slots) {
        var data = this.data, view_start = this.view_start, view_end = this.view_end;

        ctx.save();

        ctx.fillStyle = this.prefs.block_color;
        ctx.textAlign = "right";

        var y_scale = this.get_row_height(),
            feature_mapper = new FeaturePositionMapper(y_scale),
            x_draw_coords;

        for (var i = 0, len = data.length; i < len; i++) {
            var feature = data[i],
                feature_uid = feature[0],
                feature_start = feature[1],
                feature_end = feature[2],
                // Slot valid only if features are slotted and this feature is slotted; 
                // feature may not be due to lack of space.
                slot = (slots && slots[feature_uid] !== undefined ? slots[feature_uid] : null);
                
            // Draw feature if there's overlap and mode is dense or feature is slotted (as it must be for all non-dense modes).
            if ( ( feature_start < view_end && feature_end > view_start ) && (this.mode === "Dense" || slot !== null) ) {
                x_draw_coords = this.draw_element(ctx, this.mode, feature, slot, view_start, view_end, w_scale, y_scale, width);
                feature_mapper.map_feature_data(feature, slot, x_draw_coords[0], x_draw_coords[1]);
            }
        }

        ctx.restore();
        feature_mapper.y_translation = this.get_top_padding(width);
        return feature_mapper;
    },
    /** 
     * Abstract function for drawing an individual feature.
     */
    draw_element: function(ctx, mode, feature, slot, tile_low, tile_high, w_scale, y_scale, width ) {
        console.log("WARNING: Unimplemented function.");
        return [0, 0];
    }
});

// Constants specific to feature tracks moved here (HACKING, these should
// basically all be configuration options)
var DENSE_TRACK_HEIGHT = 10,
    NO_DETAIL_TRACK_HEIGHT = 3,
    SQUISH_TRACK_HEIGHT = 5,
    PACK_TRACK_HEIGHT = 10,
    NO_DETAIL_FEATURE_HEIGHT = 1,
    DENSE_FEATURE_HEIGHT = 9,
    SQUISH_FEATURE_HEIGHT = 3,
    PACK_FEATURE_HEIGHT = 9,
    LABEL_SPACING = 2,
    CONNECTOR_COLOR = "#ccc";

var LinkedFeaturePainter = function(data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler) {
    FeaturePainter.call(this, data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler);
    // Whether to draw a single connector in the background that spans the entire feature (the intron fishbone)
    this.draw_background_connector = true;
    // Whether to call draw_connector for every pair of blocks
    this.draw_individual_connectors = false;
};

extend(LinkedFeaturePainter.prototype, FeaturePainter.prototype, {

    /**
     * Height of a single row, depends on mode
     */
    get_row_height: function() {
        var mode = this.mode, height;
        if (mode === "Dense") {
            height = DENSE_TRACK_HEIGHT;            
        }
        else if (mode === "no_detail") {
            height = NO_DETAIL_TRACK_HEIGHT;
        }
        else if (mode === "Squish") {
            height = SQUISH_TRACK_HEIGHT;
        }
        else { // mode === "Pack"
            height = PACK_TRACK_HEIGHT;
        }
        return height;
    },

    /**
     * Draw a feature. Returns an array with feature's start and end X coordinates.
     */
    draw_element: function(ctx, mode, feature, slot, tile_low, tile_high, w_scale, y_scale, width) {
        var feature_uid = feature[0],
            feature_start = feature[1],
            feature_end = feature[2],
            feature_name = feature[3],
            feature_strand = feature[4],
            // -0.5 to offset region between bases.
            f_start = Math.floor( Math.max(0, (feature_start - tile_low - 0.5) * w_scale) ),
            f_end   = Math.ceil( Math.min(width, Math.max(0, (feature_end - tile_low - 0.5) * w_scale)) ),
            draw_start = f_start,
            draw_end = f_end,
            y_center = (mode === "Dense" ? 0 : (0 + slot)) * y_scale + this.get_top_padding(width),
            thickness, y_start, thick_start = null, thick_end = null,
            // TODO: is there any reason why block, label color cannot be set at the Painter level?
            // For now, assume '.' === '+'
            block_color = (!feature_strand || feature_strand === "+" || feature_strand === "." ? this.prefs.block_color : this.prefs.reverse_strand_color);
            label_color = this.prefs.label_color;
        
        // Set global alpha.
        ctx.globalAlpha = this.alpha_scaler.gen_val(feature);
        
        // In dense mode, put all data in top slot.
        if (mode === "Dense") {
            slot = 1;
        }
        
        if (mode === "no_detail") {
            // No details for feature, so only one way to display.
            ctx.fillStyle = block_color;
            ctx.fillRect(f_start, y_center + 5, f_end - f_start, NO_DETAIL_FEATURE_HEIGHT);
        } 
        else { // Mode is either Squish or Pack:
            // Feature details.
            var feature_ts = feature[5],
                feature_te = feature[6],
                feature_blocks = feature[7],
                // Whether we are drawing full height or squished features
                full_height = true;
            
            if (feature_ts && feature_te) {
                thick_start = Math.floor( Math.max(0, (feature_ts - tile_low) * w_scale) );
                thick_end = Math.ceil( Math.min(width, Math.max(0, (feature_te - tile_low) * w_scale)) );
            }
            
            // Set vars that depend on mode.
            var thin_height, thick_height;
            if (mode === "Squish" ) {
                thin_height = 1;
                thick_height = SQUISH_FEATURE_HEIGHT;
                full_height = false;
            } else if ( mode === "Dense" ) {
                thin_height = 5;
                thick_height = DENSE_FEATURE_HEIGHT;
            } else { // mode === "Pack"
                thin_height = 5;
                thick_height = PACK_FEATURE_HEIGHT;
            }
            
            // Draw feature/feature blocks + connectors.
            if (!feature_blocks) {
                // If there are no blocks, treat the feature as one big exon.
                ctx.fillStyle = block_color;
                ctx.fillRect(f_start, y_center + 1, f_end - f_start, thick_height);
                // If strand is specified, draw arrows over feature
                if ( feature_strand && full_height ) {
                    if (feature_strand === "+") {
                        ctx.fillStyle = ctx.canvas.manager.get_pattern( 'right_strand_inv' );
                    } else if (feature_strand === "-") {
                        ctx.fillStyle = ctx.canvas.manager.get_pattern( 'left_strand_inv' );
                    }
                    ctx.fillRect(f_start, y_center + 1, f_end - f_start, thick_height);
                }
            } else { 
                //
                // There are feature blocks and mode is either Squish or Pack.
                //
                // Approach: (a) draw whole feature as connector/intron and (b) draw blocks as 
                // needed. This ensures that whole feature, regardless of whether it starts with
                // a block, is visible.
                //
               
                // Compute y axis center position and height
                var cur_y_center, cur_height;
                if (mode === "Squish" || mode === "Dense") {
                    cur_y_center = y_center + Math.floor(SQUISH_FEATURE_HEIGHT/2) + 1;
                    cur_height = 1;
                }
                else { // mode === "Pack"
                    if (feature_strand) {
                        cur_y_center = y_center;
                        cur_height = thick_height;
                    }
                    else {
                        cur_y_center += (SQUISH_FEATURE_HEIGHT/2) + 1;
                        cur_height = 1;
                    }
                }

                // Draw whole feature as connector/intron.
                if ( this.draw_background_connector ) {
                    if (mode === "Squish" || mode === "Dense") {
                        ctx.fillStyle = CONNECTOR_COLOR;
                    }
                    else { // mode === "Pack"
                        if (feature_strand) {
                            if (feature_strand === "+") {
                                ctx.fillStyle = ctx.canvas.manager.get_pattern( 'right_strand' );
                            } else if (feature_strand === "-") {
                                ctx.fillStyle = ctx.canvas.manager.get_pattern( 'left_strand' );
                            }
                        }
                        else {
                            ctx.fillStyle = CONNECTOR_COLOR;
                        }
                    }
                    ctx.fillRect(f_start, cur_y_center, f_end - f_start, cur_height);
                }
                
                // Draw blocks.
                var start_and_height;
                for (var k = 0, k_len = feature_blocks.length; k < k_len; k++) {
                    var block = feature_blocks[k],
                        // -0.5 to offset block between bases.
                        block_start = Math.floor( Math.max(0, (block[0] - tile_low - 0.5) * w_scale) ),
                        block_end = Math.ceil( Math.min(width, Math.max((block[1] - tile_low - 0.5) * w_scale)) ),
                        last_block_start, last_block_end;

                    // Skip drawing if block not on tile.    
                    if (block_start > block_end) { continue; }

                    // Draw thin block.
                    ctx.fillStyle = block_color;
                    ctx.fillRect(block_start, y_center + (thick_height-thin_height)/2 + 1, block_end - block_start, thin_height);

                    // If block intersects with thick region, draw block as thick.
                    // - No thick is sometimes encoded as thick_start == thick_end, so don't draw in that case
                    if (thick_start !== undefined && feature_te > feature_ts && !(block_start > thick_end || block_end < thick_start) ) {
                        var block_thick_start = Math.max(block_start, thick_start),
                            block_thick_end = Math.min(block_end, thick_end);
                        ctx.fillRect(block_thick_start, y_center + 1, block_thick_end - block_thick_start, thick_height);
                        if ( feature_blocks.length === 1 && mode === "Pack") {
                            // Exactly one block means we have no introns, but do have a distinct "thick" region,
                            // draw arrows over it if in pack mode.
                            if (feature_strand === "+") {
                                ctx.fillStyle = ctx.canvas.manager.get_pattern( 'right_strand_inv' );
                            } else if (feature_strand === "-") {
                                ctx.fillStyle = ctx.canvas.manager.get_pattern( 'left_strand_inv' );
                            }
                            // If region is wide enough in pixels, pad a bit
                            if ( block_thick_start + 14 < block_thick_end ) {
                                block_thick_start += 2;
                                block_thick_end -= 2;
                            }
                            ctx.fillRect(block_thick_start, y_center + 1, block_thick_end - block_thick_start, thick_height);
                        }
                    }
                    // Draw individual connectors if required
                    if ( this.draw_individual_connectors && last_block_start ) {
                        this.draw_connector( ctx, last_block_start, last_block_end, block_start, block_end, y_center );
                    }
                    last_block_start = block_start;
                    last_block_end = block_end;
                }
                                
                // FIXME: Height scaling only works in Pack mode right now.
                if (mode === "Pack") {
                    // Reset alpha so height scaling is not impacted by alpha scaling.
                    ctx.globalAlpha = 1;
                    
                    // Height scaling: draw white lines to reduce height according to height scale factor.
                    ctx.fillStyle = "white"; // TODO: set this to background color.
                    var 
                        hscale_factor = this.height_scaler.gen_val(feature),
                        // Ceil ensures that min height is >= 1.
                        new_height = Math.ceil(thick_height * hscale_factor),
                        ws_height = Math.round( (thick_height-new_height)/2 );
                    if (hscale_factor !== 1) {
                        ctx.fillRect(f_start, cur_y_center + 1, f_end - f_start, ws_height);
                        ctx.fillRect(f_start, cur_y_center + thick_height - ws_height + 1, f_end - f_start, ws_height);
                    }   
                }                
            }
            
            // Reset alpha so that label is not transparent.
            ctx.globalAlpha = 1;
                        
            // Draw label for Pack mode.
            if (feature_name && mode === "Pack" && feature_start > tile_low) {
                ctx.fillStyle = label_color;
                // FIXME: assumption here that the entire view starts at 0
                if (tile_low === 0 && f_start - ctx.measureText(feature_name).width < 0) {
                    ctx.textAlign = "left";
                    ctx.fillText(feature_name, f_end + LABEL_SPACING, y_center + 8);
                    draw_end += ctx.measureText(feature_name).width + LABEL_SPACING;
                } else {
                    ctx.textAlign = "right";
                    ctx.fillText(feature_name, f_start - LABEL_SPACING, y_center + 8);
                    draw_start -= ctx.measureText(feature_name).width + LABEL_SPACING;
                }
                //ctx.fillStyle = block_color;
            }
        }
        
        // Reset global alpha.
        ctx.globalAlpha = 1;
        
        return [draw_start, draw_end];
    }
});

var ReadPainter = function(data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler, ref_seq, base_color_fn) {
    FeaturePainter.call(this, data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler);
    this.ref_seq = (ref_seq ? ref_seq.data : null);
    this.base_color_fn = base_color_fn;
};

extend(ReadPainter.prototype, FeaturePainter.prototype, {
    /**
     * Returns height based on mode.
     */
    get_row_height: function() {
        var height, mode = this.mode;
        if (mode === "Dense") {
            height = DENSE_TRACK_HEIGHT;            
        }
        else if (mode === "Squish") {
            height = SQUISH_TRACK_HEIGHT;
        }
        else { // mode === "Pack"
            height = PACK_TRACK_HEIGHT;
            if (this.prefs.show_insertions) {
                height *= 2;
            }
        }
        return height;
    },
    
    /**
     * Draw a single read.
     */
    draw_read: function(ctx, mode, w_scale, y_center, tile_low, tile_high, feature_start, cigar, strand, read_seq) {
        ctx.textAlign = "center";
        var tile_region = [tile_low, tile_high],
            base_offset = 0,
            seq_offset = 0,
            gap = Math.round(w_scale/2),
            char_width_px = ctx.canvas.manager.char_width_px,
            block_color = (strand === "+" ? this.prefs.block_color : this.prefs.reverse_strand_color),
            pack_mode = (mode === 'Pack');
            
        // Keep list of items that need to be drawn on top of initial drawing layer.
        var draw_last = [];

        // If no cigar string, then assume all matches.
        if (!cigar) {
            cigar = [ [0, read_seq.length] ];
        }

        // Draw read by processing cigar.
        for (var cig_id = 0, len = cigar.length; cig_id < len; cig_id++) {
            var cig = cigar[cig_id],
                cig_op = "MIDNSHP=X"[ cig[0] ],
                cig_len = cig[1];
            
            if (cig_op === "H" || cig_op === "S") {
                // Go left if it clips
                base_offset -= cig_len;
            }
            var seq_start = feature_start + base_offset,
                // -0.5 to offset sequence between bases.
                s_start = Math.floor( Math.max(-0.5 * w_scale, (seq_start - tile_low - 0.5) * w_scale) ),
                s_end = Math.floor( Math.max(0, (seq_start + cig_len - tile_low - 0.5) * w_scale) );
            
            // Make sure that read is drawn even if it too small to be rendered officially; in this case,
            // read is drawn at 1px.
            // TODO: need to ensure that s_start, s_end are calcuated the same for both slotting
            // and drawing.
            if (s_start === s_end) {
                s_end += 1;
            }
                
            switch (cig_op) {
                case "H": // Hard clipping.
                    // TODO: draw anything?
                    // Sequence not present, so do not increment seq_offset.
                    break;
                case "S": // Soft clipping.
                case "M": // Match.
                case "=": // Equals.
                    if (is_overlap([seq_start, seq_start + cig_len], tile_region)) {
                        // Draw read base as rectangle.
                        ctx.fillStyle = block_color;
                        ctx.fillRect(s_start, 
                                     y_center + (pack_mode ? 1 : 4 ), 
                                     s_end - s_start, 
                                     (pack_mode ? PACK_FEATURE_HEIGHT : SQUISH_FEATURE_HEIGHT));

                        // Draw sequence and/or variants.
                        var seq = read_seq.slice(seq_offset, seq_offset + cig_len),
                            ref_char,
                            read_char,
                            x_pos;
                        for (var c = 0, str_len = seq.length; c < str_len; c++) {
                            // Draw base if it's on tile:
                            if (seq_start + c >= tile_low && seq_start + c <= tile_high) {
                                // Get reference and read character.
                                ref_char = (this.ref_seq ? this.ref_seq[seq_start - tile_low + c] : null);
                                read_char = seq[c];
                                x_pos = Math.floor( Math.max(0, (seq_start + c - tile_low) * w_scale) );

                                // Draw base depending on (a) available reference data and (b) config options.
                                if (
                                    // If there's reference data and (a) showing all (i.e. not showing 
                                    // differences) or (b) if there is a variant.
                                    (ref_char && 
                                        (!this.prefs.show_differences || 
                                        (read_char.toLowerCase !== 'n' && (ref_char.toLowerCase() !== read_char.toLowerCase())))
                                    ) ||
                                    // If there's no reference data and showing all.
                                    (!ref_char && !this.prefs.show_differences)
                                    ) {

                                    // Draw base.
                                    var c_start = Math.floor( Math.max(0, (seq_start + c - tile_low) * w_scale) );
                                    ctx.fillStyle = this.base_color_fn(seq[c]);
                                    if (pack_mode && w_scale > char_width_px) {
                                        ctx.fillText(seq[c], c_start, y_center + 9);
                                    }
                                    // Require a minimum w_scale so that variants are only drawn when somewhat zoomed in.
                                    else if (w_scale > 0.05) {
                                        ctx.fillRect(c_start, 
                                                     y_center + (pack_mode ? 1 : 4), 
                                                     Math.max( 1, Math.round(w_scale) ),
                                                     (pack_mode ? PACK_FEATURE_HEIGHT : SQUISH_FEATURE_HEIGHT));
                                    }
                                }

                            }
                        }
                    }
                    seq_offset += cig_len;
                    base_offset += cig_len;
                    break;
                case "N": // Skipped bases.
                    ctx.fillStyle = CONNECTOR_COLOR;
                    ctx.fillRect(s_start, y_center + 5, s_end - s_start, 1);
                    //ctx.dashedLine(s_start + this.left_offset, y_center + 5, this.left_offset + s_end, y_center + 5);
                    // No change in seq_offset because sequence not used when skipping.
                    base_offset += cig_len;
                    break;
                case "D": // Deletion.
                    ctx.fillStyle = "red";
                    ctx.fillRect(s_start, y_center + 4, s_end - s_start, 3);
                    // TODO: is this true? No change in seq_offset because sequence not used when skipping.
                    base_offset += cig_len;
                    break;
                case "P": // TODO: No good way to draw insertions/padding right now, so ignore
                    // Sequences not present, so do not increment seq_offset.
                    break;
                case "I": // Insertion.
                    // Check to see if sequence should be drawn at all by looking at the overlap between
                    // the sequence region and the tile region.
                    var insert_x_coord = s_start - gap;
                    
                    if (is_overlap([seq_start, seq_start + cig_len], tile_region)) {
                        var seq = read_seq.slice(seq_offset, seq_offset + cig_len);
                        // Insertion point is between the sequence start and the previous base: (-gap) moves
                        // back from sequence start to insertion point.
                        if (this.prefs.show_insertions) {
                            //
                            // Show inserted sequence above, centered on insertion point.
                            //

                            // Draw sequence.
                            // X center is offset + start - <half_sequence_length>
                            var x_center = s_start - (s_end - s_start)/2;
                            if ( (mode === "Pack" || this.mode === "Auto") && read_seq !== undefined && w_scale > char_width_px) {
                                // Draw sequence container.
                                ctx.fillStyle = "yellow";
                                ctx.fillRect(x_center - gap, y_center - 9, s_end - s_start, 9);
                                draw_last[draw_last.length] = {type: "triangle", data: [insert_x_coord, y_center + 4, 5]};
                                ctx.fillStyle = CONNECTOR_COLOR;
                                // Based on overlap b/t sequence and tile, get sequence to be drawn.
                                switch( compute_overlap( [seq_start, seq_start + cig_len], tile_region ) ) {
                                    case(OVERLAP_START):
                                        seq = seq.slice(tile_low-seq_start);
                                        break;
                                    case(OVERLAP_END):
                                        seq = seq.slice(0, seq_start-tile_high);
                                        break;
                                    case(CONTAINED_BY):
                                        // All of sequence drawn.
                                        break;
                                    case(CONTAINS):
                                        seq = seq.slice(tile_low-seq_start, seq_start-tile_high);
                                        break;
                                }
                                // Draw sequence.
                                for (var c = 0, str_len = seq.length; c < str_len; c++) {
                                    var c_start = Math.floor( Math.max(0, (seq_start + c -  tile_low) * w_scale) );
                                    ctx.fillText(seq[c], c_start - (s_end - s_start)/2, y_center);
                                }
                            }
                            else {
                                // Draw block.
                                ctx.fillStyle = "yellow";
                                // TODO: This is a pretty hack-ish way to fill rectangle based on mode.
                                ctx.fillRect(x_center, y_center + (this.mode !== "Dense" ? 2 : 5), 
                                             s_end - s_start, (mode !== "Dense" ? SQUISH_FEATURE_HEIGHT : DENSE_FEATURE_HEIGHT));
                            }
                        }
                        else {
                            if ( (mode === "Pack" || this.mode === "Auto") && read_seq !== undefined && w_scale > char_width_px) {
                                // Show insertions with a single number at the insertion point.
                                draw_last.push( { type: "text", data: [seq.length, insert_x_coord, y_center + 9] } );
                            }
                            else {
                                // TODO: probably can merge this case with code above.
                            }
                        }
                    }
                    seq_offset += cig_len;
                    // No change to base offset because insertions are drawn above sequence/read.
                    break;
                case "X":
                    // TODO: draw something?
                    seq_offset += cig_len;
                    break;
            }
        }
        
        //
        // Draw last items.
        //
        ctx.fillStyle = "yellow";
        var item, type, data;
        for (var i = 0; i < draw_last.length; i++) {
            item = draw_last[i];
            type = item.type;
            data = item.data;
            if (type === "text") {
                ctx.save();
                ctx.font = "bold " + ctx.font;
                ctx.fillText(data[0], data[1], data[2]);
                ctx.restore();
            }
            else if (type === "triangle") {
                drawDownwardEquilateralTriangle(ctx, data[0], data[1], data[2]);
            }
        }
    },
    
    /**
     * Draw a complete read pair
     */
    draw_element: function(ctx, mode, feature, slot, tile_low, tile_high, w_scale, y_scale, width ) {
        // All features need a start, end, and vertical center.
        var feature_uid = feature[0],
            feature_start = feature[1],
            feature_end = feature[2],
            feature_name = feature[3],
            // -0.5 to put element between bases.
            f_start = Math.floor( Math.max(-0.5 * w_scale, (feature_start - tile_low - 0.5) * w_scale) ),
            f_end   = Math.ceil( Math.min(width, Math.max(0, (feature_end - tile_low - 0.5) * w_scale)) ),
            y_center = (mode === "Dense" ? 0 : (0 + slot)) * y_scale,
            label_color = this.prefs.label_color;
        
        // Draw read.
        if (feature[5] instanceof Array) {
            // Read is paired.
            var b1_start = Math.floor( Math.max(0, (feature[4][0] - tile_low) * w_scale) ),
                b1_end   = Math.ceil( Math.min(width, Math.max(0, (feature[4][1] - tile_low) * w_scale)) ),
                b2_start = Math.floor( Math.max(0, (feature[5][0] - tile_low) * w_scale) ),
                b2_end   = Math.ceil( Math.min(width, Math.max(0, (feature[5][1] - tile_low) * w_scale)) ),
                connector = true;

            // Draw left/forward read.
            if (feature[4][1] >= tile_low && feature[4][0] <= tile_high && feature[4][2]) {                
                this.draw_read(ctx, mode, w_scale, y_center, tile_low, tile_high, feature[4][0], feature[4][2], feature[4][3], feature[4][4]);
            }
            else {
                connector = false;
            }

            // Draw right/reverse read.
            if (feature[5][1] >= tile_low && feature[5][0] <= tile_high && feature[5][2]) {
                this.draw_read(ctx, mode, w_scale, y_center, tile_low, tile_high, feature[5][0], feature[5][2], feature[5][3], feature[5][4]);
            }
            else {
                connector = false;
            }

            // Draw connector if both reads were drawn.
            // TODO: currently, there is no way to connect reads drawn on different tiles; to connect reads on different tiles, data manager
            // code is needed to join mate pairs from different regions. Alternatively, requesting multiple regions of data at once would
            // make it possible to put together more easily.
            if (connector && b2_start > b1_end) {
                ctx.fillStyle = CONNECTOR_COLOR;
                dashedLine(ctx, b1_end, y_center + 5, b2_start, y_center + 5);
            }
        } else {
            // Read is single.
            this.draw_read(ctx, mode, w_scale, y_center, tile_low, tile_high, feature_start, feature[4], feature[5], feature[6]);
        }
        if (mode === "Pack" && feature_start >= tile_low && feature_name !== ".") {
            // Draw label.
            ctx.fillStyle = this.prefs.label_color;
            if (tile_low === 0 && f_start - ctx.measureText(feature_name).width < 0) {
                ctx.textAlign = "left";
                ctx.fillText(feature_name, f_end + LABEL_SPACING, y_center + 8);
            } else {
                ctx.textAlign = "right";
                ctx.fillText(feature_name, f_start - LABEL_SPACING, y_center + 8);
            }
        }
        
        // FIXME: provide actual coordinates for drawn read.
        return [0,0];
    }
});

var ArcLinkedFeaturePainter = function(data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler) {
    LinkedFeaturePainter.call(this, data, view_start, view_end, prefs, mode, alpha_scaler, height_scaler);
    // Need to know the longest feature length for adding spacing
    this.longest_feature_length = this.calculate_longest_feature_length();
    this.draw_background_connector = false;
    this.draw_individual_connectors = true;
};

extend(ArcLinkedFeaturePainter.prototype, FeaturePainter.prototype, LinkedFeaturePainter.prototype, {

    calculate_longest_feature_length: function () {
        var longest_feature_length = 0;
        for (var i = 0, len = this.data.length; i < len; i++) {
            var feature = this.data[i], feature_start = feature[1], feature_end = feature[2];
            longest_feature_length = Math.max( longest_feature_length, feature_end - feature_start );
        }
        return longest_feature_length;
    },

    get_top_padding: function( width ) { 
        var view_range = this.view_end - this.view_start,
            w_scale = width / view_range;
        return Math.min( 128, Math.ceil( ( this.longest_feature_length / 2 ) * w_scale ) );
    },

    draw_connector: function( ctx, block1_start, block1_end, block2_start, block2_end, y_center ) {
        // Arc drawing -- from closest endpoints
        var x_center = ( block1_end + block2_start ) / 2,
            radius = block2_start - x_center; 
        // For full half circles
        var angle1 = Math.PI, angle2 = 0;
        if ( radius > 0 ) {
            ctx.beginPath();
            ctx.arc( x_center, y_center, block2_start - x_center, Math.PI, 0 );
            ctx.stroke();
        }
    }
});

// Color stuff from less.js

var Color = function (rgb, a) {
    /**
     * The end goal here, is to parse the arguments
     * into an integer triplet, such as `128, 255, 0`
     *
     * This facilitates operations and conversions.
     */
    if (Array.isArray(rgb)) {
        this.rgb = rgb;
    } else if (rgb.length == 6) {
        this.rgb = rgb.match(/.{2}/g).map(function (c) {
            return parseInt(c, 16);
        });
    } else if (rgb.length == 7) {
        this.rgb = rgb.substring(1,7).match(/.{2}/g).map(function (c) {
            return parseInt(c, 16);
        });
    } else {
        this.rgb = rgb.split('').map(function (c) {
            return parseInt(c + c, 16);
        });
    }
    this.alpha = typeof(a) === 'number' ? a : 1;
};
Color.prototype = {
    eval: function () { return this; },

    //
    // If we have some transparency, the only way to represent it
    // is via `rgba`. Otherwise, we use the hex representation,
    // which has better compatibility with older browsers.
    // Values are capped between `0` and `255`, rounded and zero-padded.
    //
    toCSS: function () {
        if (this.alpha < 1.0) {
            return "rgba(" + this.rgb.map(function (c) {
                return Math.round(c);
            }).concat(this.alpha).join(', ') + ")";
        } else {
            return '#' + this.rgb.map(function (i) {
                i = Math.round(i);
                i = (i > 255 ? 255 : (i < 0 ? 0 : i)).toString(16);
                return i.length === 1 ? '0' + i : i;
            }).join('');
        }
    },

    toHSL: function () {
        var r = this.rgb[0] / 255,
            g = this.rgb[1] / 255,
            b = this.rgb[2] / 255,
            a = this.alpha;

        var max = Math.max(r, g, b), min = Math.min(r, g, b);
        var h, s, l = (max + min) / 2, d = max - min;

        if (max === min) {
            h = s = 0;
        } else {
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2;               break;
                case b: h = (r - g) / d + 4;               break;
            }
            h /= 6;
        }
        return { h: h * 360, s: s, l: l, a: a };
    },

    toARGB: function () {
        var argb = [Math.round(this.alpha * 255)].concat(this.rgb);
        return '#' + argb.map(function (i) {
            i = Math.round(i);
            i = (i > 255 ? 255 : (i < 0 ? 0 : i)).toString(16);
            return i.length === 1 ? '0' + i : i;
        }).join('');
    },

    mix: function (color2, weight) {
        color1 = this;

        var p = weight; // .value / 100.0;
        var w = p * 2 - 1;
        var a = color1.toHSL().a - color2.toHSL().a;

        var w1 = (((w * a == -1) ? w : (w + a) / (1 + w * a)) + 1) / 2.0;
        var w2 = 1 - w1;

        var rgb = [color1.rgb[0] * w1 + color2.rgb[0] * w2,
                   color1.rgb[1] * w1 + color2.rgb[1] * w2,
                   color1.rgb[2] * w1 + color2.rgb[2] * w2];

        var alpha = color1.alpha * p + color2.alpha * (1 - p);

        return new Color(rgb, alpha);
    }
};


// End colors from less.js

var LinearRamp = function( start_color, end_color, start_value, end_value ) {
    /**
     * Simple linear gradient
     */
    this.start_color = new Color( start_color );
    this.end_color = new Color( end_color );
    this.start_value = start_value;
    this.end_value = end_value;
    this.value_range = end_value - start_value;
};

LinearRamp.prototype.map_value = function( value ) {
    value = Math.max( value, this.start_value );
    value = Math.min( value, this.end_value );
    value = ( value - this.start_value ) / this.value_range;
    // HACK: just red for now
    // return "hsl(0,100%," + (value * 100) + "%)"
    return this.start_color.mix( this.end_color, 1 - value ).toCSS();
};

var SplitRamp = function( start_color, middle_color, end_color, start_value, end_value ) {
    /**
     * Two gradients split away from 0
     */
    this.positive_ramp = new LinearRamp( middle_color, end_color, 0, end_value );
    this.negative_ramp = new LinearRamp( middle_color, start_color, 0, -start_value );
    this.start_value = start_value;
    this.end_value = end_value;
};

SplitRamp.prototype.map_value = function( value ) {
    value = Math.max( value, this.start_value );
    value = Math.min( value, this.end_value );
    if ( value >= 0 ) {
        return this.positive_ramp.map_value( value );
    } else {
        return this.negative_ramp.map_value( -value );
    }
};

var DiagonalHeatmapPainter = function(data, view_start, view_end, prefs, mode) {
    Painter.call( this, data, view_start, view_end, prefs, mode );
    var i, len;
    if ( this.prefs.min_value === undefined ) {
        var min_value = Infinity;
        for (i = 0, len = this.data.length; i < len; i++) {
            min_value = Math.min( min_value, this.data[i][5] );
        }
        this.prefs.min_value = min_value;
    }
    if ( this.prefs.max_value === undefined ) {
        var max_value = -Infinity;
        for (i = 0, len = this.data.length; i < len; i++) {
            max_value = Math.max( max_value, this.data[i][5] );
        }
        this.prefs.max_value = max_value;
    }
};

DiagonalHeatmapPainter.prototype.default_prefs = { 
    min_value: undefined, 
    max_value: undefined, 
    mode: "Heatmap", 
    pos_color: "#FF8C00",
    neg_color: "#4169E1" 
};

DiagonalHeatmapPainter.prototype.draw = function(ctx, width, height, w_scale) {
    var 
        min_value = this.prefs.min_value,
        max_value = this.prefs.max_value,
        value_range = max_value - min_value,
        height_px = height,
        view_start = this.view_start,
        mode = this.mode,
        data = this.data,
        invsqrt2 = 1 / Math.sqrt(2);

    var ramp = ( new SplitRamp( this.prefs.neg_color, "#FFFFFF", this.prefs.pos_color, min_value, max_value ) );

    var d, s1, e1, s2, e2, value;

    var scale = function( p ) { return ( p - view_start ) * w_scale; };

    ctx.save();

    // Draw into triangle, then rotate and scale
    ctx.rotate(-45 * Math.PI / 180);
    ctx.scale( invsqrt2, invsqrt2 );
    
    // Paint track.
    for (var i = 0, len = data.length; i < len; i++) {

        d = data[i];

        // Ensure the cell is visible
        // if ( )

        s1 = scale( d[1] );
        e1 = scale( d[2] );
        s2 = scale( d[4] );
        e2 = scale( d[5] );
        value = d[6];

        //console.log( "!!!", value, ramp.map_value( value ) );

        ctx.fillStyle = ( ramp.map_value( value ) );

        ctx.fillRect( s1, s2, ( e1 - s1 ), ( e2 - s2 ) );
    }
    
    ctx.restore();
};

return {
    Scaler: Scaler,
    SummaryTreePainter: SummaryTreePainter,
    LinePainter: LinePainter,
    LinkedFeaturePainter: LinkedFeaturePainter,
    ReadPainter: ReadPainter,
    ArcLinkedFeaturePainter: ArcLinkedFeaturePainter,
    DiagonalHeatmapPainter: DiagonalHeatmapPainter
};


});
