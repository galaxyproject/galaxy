// External dependencies (for module management eventually): jQuery, Backbone, underscore

// This is necessary so that, when nested arrays are used in ajax/post/get methods, square brackets ('[]') are
// not appended to the identifier of a nested array.
jQuery.ajaxSettings.traditional = true;

/**
 * A Galaxy grid.
 */
var Grid = Backbone.Model.extend({
    defaults: {
        url_base: '',
        async: false,
        async_ops: [],
        categorical_filters: [],
        filters: {},
        sort_key: null,
        show_item_checkboxes: false,
        cur_page: 1,
        num_pages: 1,
        operation: undefined,
        item_ids: undefined
    },

    /**
     * Return true if operation can be done asynchronously.
     */
    can_async_op: function(op) {
        return _.indexOf(this.attributes.async_ops, op) !== -1;
    },

    /**
     * Add filtering criterion.
     */
    add_filter: function(key, value, append) {
        // Update URL arg with new condition.            
        if (append) {
            // Update or append value.
            var cur_val = this.attributes.filters[key],
                new_val;
            if (cur_val === null || cur_val === undefined) {
                new_val = value;
            } 
            else if (typeof(cur_val) == "string") {
                if (cur_val == "All") {
                    new_val = value;
                } else {
                    // Replace string with array.
                    var values = [];
                    values[0] = cur_val;
                    values[1] = value;
                    new_val = values;   
                }
            } 
            else {
                // Current value is an array.
                new_val = cur_val;
                new_val.push(value);
            }
            this.attributes.filters[key] = new_val;
        } 
        else {
            // Replace value.
            this.attributes.filters[key] = value;
        }
    },

    /**
     * Remove filtering criterion.
     */
    remove_filter: function(key, condition) {
        var cur_val = this.attributes.filters[key];
        if (cur_val === null || cur_val === undefined) {
            return false;            
        }

        var removed = true;
        if (typeof(cur_val) === "string") {
            if (cur_val == "All") {
                // Unexpected. Throw error?
                removed = false;
            } 
            else {
                // Remove condition.
                delete this.attributes.filters[key];
            }
        }
        else {
            // Filter contains an array of conditions.
            var condition_index = _.indexOf(cur_val, condition);
            if (condition_index !== -1) {
                cur_val.splice(condition_index, 1);
            }
            else {
                removed = false;
            }
        }

        return removed;
    },

    /**
     * Returns URL data for obtaining a new grid.
     */
    get_url_data: function() {
        var url_data = {
            async: this.attributes.async,
            sort: this.attributes.sort_key,
            page: this.attributes.cur_page,
            show_item_checkboxes: this.attributes.show_item_checkboxes
        };

        // Add operation, item_ids only if they have values.
        if (this.attributes.operation) {
            url_data.operation = this.attributes.operation;
        }
        if (this.attributes.item_ids) {
            url_data.id = this.attributes.item_ids;
        }

        // Add filter arguments to data, placing "f-" in front of all arguments.
        // FIXME: when underscore updated, use pairs function().
        var self = this;
        _.each(_.keys(self.attributes.filters), function(k) {
            url_data['f-' + k] = self.attributes.filters[k];
        });

        return url_data;
    }
});

//
// Code to handle grid operations: filtering, sorting, paging, and operations.
//

// Init operation buttons.
function init_operation_buttons() {
    // Initialize operation buttons.
    $('input[name=operation]:submit').each(function() {
        $(this).click( function() {
           var operation_name = $(this).val();
           // For some reason, $('input[name=id]:checked').val() does not return all ids for checked boxes.
           // The code below performs this function.
           var item_ids = [];
           $('input[name=id]:checked').each(function() {
               item_ids.push( $(this).val() );
           });
           do_operation(operation_name, item_ids); 
        });
    });
}

// Initialize grid controls
function init_grid_controls() {
    init_operation_buttons();    
    
    // Initialize submit image elements.
    $('.submit-image').each( function() {
        // On mousedown, add class to simulate click.
        $(this).mousedown( function() {
           $(this).addClass('gray-background'); 
        });
        
        // On mouseup, add class to simulate click.
        $(this).mouseup( function() {
           $(this).removeClass('gray-background'); 
        });
    });
    
    // Initialize sort links.
    $('.sort-link').each( function() {
        $(this).click( function() {
           set_sort_condition( $(this).attr('sort_key') );
           return false;
        });
    });
    
    // Initialize page links.
    $('.page-link > a').each( function() {
        $(this).click( function() {
           set_page( $(this).attr('page_num') );
           return false;
        });
    });

    // Initialize categorical filters.
    $('.categorical-filter > a').each( function() {
        $(this).click( function() {
            set_categorical_filter( $(this).attr('filter_key'), $(this).attr('filter_val') );
            return false;
        });
    });
    
    // Initialize text filters.
    $('.text-filter-form').each( function() {
        $(this).submit( function() {
            var column_key = $(this).attr('column_key');
            var text_input_obj = $('#input-' + column_key + '-filter');
            var text_input = text_input_obj.val();
            text_input_obj.val('');
            add_filter_condition(column_key, text_input, true);
            return false;
        });
    });
    
    // Initialize autocomplete for text inputs in search UI.
    var t = $("#input-tags-filter");
    if (t.length) {
        t.autocomplete(history_tag_autocomplete_url, 
                       { selectFirst: false, autoFill: false, highlight: false, mustMatch: false });
    }

    var t2 = $("#input-name-filter");
    if (t2.length) {
        t2.autocomplete(history_name_autocomplete_url,
                        { selectFirst: false, autoFill: false, highlight: false, mustMatch: false });
    }
    
    // Initialize standard, advanced search toggles.
    $('.advanced-search-toggle').each( function() {
        $(this).click( function() {
            $("#standard-search").slideToggle('fast');
            $('#advanced-search').slideToggle('fast');
            return false;
        });
    });
}

// Initialize grid elements.
function init_grid_elements() {
    // Initialize grid selection checkboxes.
    $(".grid").each( function() {
        var checkboxes = $(this).find("input.grid-row-select-checkbox");
        var check_count = $(this).find("span.grid-selected-count");
        var update_checked = function() {
            check_count.text( $(checkboxes).filter(":checked").length );
        };
        
        $(checkboxes).each( function() {
            $(this).change(update_checked);
        });
        update_checked();
    });
    
    // Initialize item labels.
    $(".label").each( function() {
        // If href has an operation in it, do operation when clicked. Otherwise do nothing.
        var href = $(this).attr('href');
        if ( href !== undefined && href.indexOf('operation=') != -1 ) {
            $(this).click( function() {
                do_operation_from_href( $(this).attr('href') );
                return false;
            });   
        }
    });
    
    // Initialize ratings.
    $('.community_rating_star').rating({});
    
    // Initialize item menu operations.
    make_popup_menus();
}

// Go back to page one; this is useful when a filter is applied.
function go_page_one() {
    // Need to go back to page 1 if not showing all.
    var cur_page = grid.get('cur_page');
    if (cur_page !== null && cur_page !== undefined && cur_page !== 'all') {
        grid.set('cur_page', 1);
    }               
}

// Add a condition to the grid filter; this adds the condition and refreshes the grid.
function add_filter_condition(name, value, append) {
    // Do nothing is value is empty.
    if (value === "") {
        return false;
    }
    
    // Add condition to grid.
    grid.add_filter(name, value, append);
    
    // Add button that displays filter and provides a button to delete it.
    var t = $("<span>" + value + "<a href='javascript:void(0);'><span class='delete-search-icon' /></a></span>");
    t.addClass('text-filter-val');
    t.click(function() {
        // Remove filter condition.
        grid.remove_filter(name, value);

        // Remove visible element.
        $(this).remove();

        go_page_one();
        update_grid();
    });
    
    var container = $('#' + name + "-filtering-criteria");
    container.append(t);
    
    go_page_one();
    update_grid();
}

// Add tag to grid filter.
function add_tag_to_grid_filter(tag_name, tag_value) {
    // Put tag name and value together.
    var tag = tag_name + (tag_value !== undefined && tag_value !== "" ? ":" + tag_value : "");
    $('#advanced-search').show('fast');
    add_filter_condition("tags", tag, true); 
}

// Set sort condition for grid.
function set_sort_condition(col_key) {
    // Set new sort condition. New sort is col_key if sorting new column; if reversing sort on
    // currently sorted column, sort is reversed.
    var cur_sort = grid.get('sort_key');
    var new_sort = col_key;
    if (cur_sort.indexOf(col_key) !== -1) {
        // Reverse sort.
        if (cur_sort.substring(0,1) !== '-') {
            new_sort = '-' + col_key;
        } else { 
            // Sort reversed by using just col_key.
        }
    }
    
    // Remove sort arrows elements.
    $('.sort-arrow').remove();
    
    // Add sort arrow element to new sort column.
    var sort_arrow = (new_sort.substring(0,1) == '-') ? "&uarr;" : "&darr;";
    var t = $("<span>" + sort_arrow + "</span>").addClass('sort-arrow');
    var th = $("#" + col_key + '-header');
    th.append(t);
    
    // Update grid.
    grid.set('sort_key', new_sort);
    go_page_one();
    update_grid();
}

// Set new value for categorical filter.
function set_categorical_filter(name, new_value) {
    // Update filter hyperlinks to reflect new filter value.
    var category_filter = grid.get('categorical_filters')[name],
        cur_value = grid.get('filters')[name];
    $("." + name + "-filter").each( function() {
        var text = $.trim( $(this).text() );
        var filter = category_filter[text];
        var filter_value = filter[name];
        if (filter_value == new_value) {
            // Remove filter link since grid will be using this filter. It is assumed that
            // this element has a single child, a hyperlink/anchor with text.
            $(this).empty();
            $(this).addClass("current-filter");
            $(this).append(text);
        } else if (filter_value == cur_value) {
            // Add hyperlink for this filter since grid will no longer be using this filter. It is assumed that
            // this element has a single child, a hyperlink/anchor.
            $(this).empty();
            var t = $("<a href='#'>" + text + "</a>");
            t.click(function() {
                set_categorical_filter( name, filter_value ); 
            });
            $(this).removeClass("current-filter");
            $(this).append(t);
        }
    });
    
    // Update grid.
    grid.add_filter(name, new_value);
    go_page_one();
    update_grid();
}

// Set page to view.
function set_page(new_page) {
    // Update page hyperlink to reflect new page.
    $(".page-link").each( function() {
        var id = $(this).attr('id'),
            page_num = parseInt( id.split("-")[2], 10 ), // Id has form 'page-link-<page_num>
            cur_page = grid.get('cur_page'),
            text;
        if (page_num === new_page) {
            // Remove link to page since grid will be on this page. It is assumed that
            // this element has a single child, a hyperlink/anchor with text.
            text = $(this).children().text();
            $(this).empty();
            $(this).addClass("inactive-link");
            $(this).text(text);
        } 
        else if (page_num === cur_page) {
            // Add hyperlink to this page since grid will no longer be on this page. It is assumed that
            // this element has a single child, a hyperlink/anchor.
            text = $(this).text();
            $(this).empty();
            $(this).removeClass("inactive-link");
            var t = $("<a href='#'>" + text + "</a>");
            t.click(function() {
              set_page(page_num); 
            });
            $(this).append(t);
        }
    });

    var maintain_page_links = true;
    if (new_page === "all") {
        grid.set('cur_page', new_page);
        maintain_page_links = false;
    } else {
        grid.set('cur_page', parseInt(new_page, 10));
    }
    update_grid(maintain_page_links);
}

// Perform a grid operation.
function do_operation(operation, item_ids) {
    operation = operation.toLowerCase();

    // Update grid.
    grid.set({
        operation: operation,
        item_ids: item_ids
    });
    
    // Do operation. If operation cannot be performed asynchronously, redirect to location.
    if (grid.can_async_op(operation)) {
        update_grid(true);
    }
    else {
        go_to_URL();
    }
}

// Perform a hyperlink click that initiates an operation. If there is no operation, ignore click.
function do_operation_from_href(href) {
    // Get operation, id in hyperlink's href.
    var href_parts = href.split("?");
    if (href_parts.length > 1) {
        var href_parms_str = href_parts[1];
        var href_parms = href_parms_str.split("&");
        var operation = null;
        var id = -1;
        for (var index = 0; index < href_parms.length; index++) {
            if (href_parms[index].indexOf('operation') != -1) {
                // Found operation parm; get operation value. 
                operation = href_parms[index].split('=')[1];
            } else if (href_parms[index].indexOf('id') != -1) {
                // Found id parm; get id value.
                id = href_parms[index].split('=')[1];
            }
        }
        // Do operation.
        do_operation(operation, id);
        return false;
    }
}

// Navigate window to the URL defined by url_args. This method can be used to short-circuit grid AJAXing.
function go_to_URL() {
    // Not async request.
    grid.set('async', false);
    
    // Go.
    window.location = grid.get('url_base') + "?" + $.param(grid.get_url_data());
}

// Update grid.
function update_grid(maintain_page_links) {
    // If grid is not using async, then go to URL.
    if (!grid.get('async')) {
        go_to_URL();
        return;
    }
    
    // If there's an operation, do POST; otherwise, do GET.
    var method = (grid.get('operation') ? "POST" : "GET" );
    $('.loading-elt-overlay').show(); // Show overlay to indicate loading and prevent user actions.
    $.ajax({
        type: method,
        url: grid.get('url_base'),
        data: grid.get_url_data(),
        error: function() { alert( "Grid refresh failed" ); },
        success: function(response_text) {
            // HACK: use a simple string to separate the elements in the
            // response: (1) table body; (2) number of pages in table; and (3) message.
            var parsed_response_text = response_text.split("*****");
            
            // Update grid body and footer.
            $('#grid-table-body').html(parsed_response_text[0]);
            // FIXME: this does not work at all; what's needed is a function
            // that updates page links when number of pages changes.
            $('#grid-table-footer').html(parsed_response_text[1]);
            
            // Trigger custom event to indicate grid body has changed.
            $('#grid-table-body').trigger('update');
            
            // Init grid.
            init_grid_elements();
            init_operation_buttons();
            make_popup_menus();
            
            // Hide loading overlay.
            $('.loading-elt-overlay').hide();
            
            // Show message if there is one.
            var message = $.trim( parsed_response_text[2] );
            if (message !== "") {
                $('#grid-message').html( message ).show();
                setTimeout( function() { $('#grid-message').hide(); }, 5000);
            }
        },
        complete: function() {
            // Clear grid of transient request attributes.
            grid.set({
                operation: undefined,
                item_ids: undefined
            });
        }
    });    
}

function check_all_items() {
    var chk_all = document.getElementById('check_all'),
        checks = document.getElementsByTagName('input'),
        total = 0,
        i;
    if ( chk_all.checked === true ) {
        for ( i=0; i < checks.length; i++ ) {
            if ( checks[i].name.indexOf( 'id' ) !== -1) {
               checks[i].checked = true;
               total++;
            }
        }
    }
    else {
        for ( i=0; i < checks.length; i++ ) {
            if ( checks[i].name.indexOf( 'id' ) !== -1) {
               checks[i].checked = false;
            }
        }
    }
    init_grid_elements();
}