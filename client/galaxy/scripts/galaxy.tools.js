// dependencies
define([ "libs/underscore", "mvc/tools" ], function( _, Tools ) {

    var checkUncheckAll = function( name, check ) {
        $("input[name='" + name + "'][type='checkbox']").attr('checked', !!check);
    }

    $(".tool-share-link").each( function() {
        var href = $(this).attr("href");
        var href = $(this).attr("data-link");
        $(this).click(function() {
            window.prompt("Copy to clipboard: Ctrl+C, Enter", href);
        });
    });

    // Inserts the Select All / Unselect All buttons for checkboxes
    $("div.checkUncheckAllPlaceholder").each( function() {
        var check_name = $(this).attr("checkbox_name");
        select_link = $("<a class='action-button'></a>").text("Select All").click(function() {
           checkUncheckAll(check_name, true);
        });
        unselect_link = $("<a class='action-button'></a>").text("Unselect All").click(function() {
           checkUncheckAll(check_name, false);
        });
        $(this).append(select_link).append(" ").append(unselect_link);
    });

    var SELECTION_TYPE = {
        'select_single': {
            'icon_class': 'fa-file-o',
            'select_by': 'Run tool on single input',
            'allow_remap': true
        },
        'select_multiple': {
            'icon_class': 'fa-files-o',
            'select_by': 'Run tool in parallel across multiple datasets',
            'allow_remap': false,
            'min_option_count': 2 // Don't show multiple select switch if only
                                  // one dataset available.
        },
        'select_collection': {
            'icon_class': 'fa-folder-o',
            'select_by': 'Run tool in parallel across dataset collection',
            'allow_remap': false
        },
        'multiselect_single': {
            'icon_class': 'fa-list-alt',
            'select_by': 'Run tool over multiple datasets',
            'allow_remap': true
        },
        'multiselect_collection': {
            'icon_class': 'fa-folder-o',
            'select_by': 'Run tool over dataset collection',
            'allow_remap': false,
        },
        'select_single_collection': {
            'icon_class': 'fa-file-o',
            'select_by': 'Run tool on single collection',
            'allow_remap': true
        },
        'select_map_over_collections': {
            'icon_class': 'fa-folder-o',
            'select_by': 'Map tool over compontents of nested collection',
            'allow_remap': false,            
        }
    };

    var SwitchSelectView = Backbone.View.extend({
        initialize: function( data ) {
            var defaultOption = data.default_option;
            var defaultIndex = null;
            var switchOptions = data.switch_options;
            this.switchOptions = switchOptions;
            this.prefix = data.prefix;
            var el = this.$el;
            var view = this;

            var index = 0;
            var visibleCount = 0;
            _.each( this.switchOptions, function( option, onValue ) {
                var numValues = _.size( option.options );
                var selectionType = SELECTION_TYPE[ onValue ];
                var iIndex = index++;
                var hidden = false;
                if( defaultOption == onValue ) {
                    defaultIndex = iIndex;
                } else if( numValues < ( selectionType.min_option_count || 1 ) ) {
                    hidden = true;
                }
                if( ! hidden ) {
                    visibleCount++;
                    var button = $('<i class="fa ' + selectionType['icon_class'] + ' runOptionIcon" style="padding-left: 5px; padding-right: 2px;"></i>').click(function() {
                        view.enableSelectBy( iIndex, onValue );
                    }).attr(
                        'title',
                        selectionType['select_by']
                    ).data( "index", iIndex );
                    view.formRow().find( "label" ).append( button );
                }
            });
            if( visibleCount < 2 ) {
                // Don't show buttons to switch options...
                view.formRow().find("i.runOptionIcon").hide();
            }

            if( defaultIndex != null) {
                view.enableSelectBy( defaultIndex, defaultOption );
            }
        },

        formRow: function() {
            return this.$el.closest( ".form-row" );
        },

        render: function() {
        },

        enableSelectBy: function( enableIndex, onValue ) {
            var selectionType = SELECTION_TYPE[onValue];
            if(selectionType["allow_remap"]) {
                $("div#remap-row").css("display", "inherit");
            } else {
                $("div#remap-row").css("display", "none");
            }
            this.formRow().find( "i" ).each(function(_, iElement) {
                var $iElement = $(iElement);
                var index = $iElement.data("index");
                if(index == enableIndex) {
                    $iElement.css('color', 'black');
                } else {
                    $iElement.css('color', 'Gray');
                }
            });
            var $select = this.$( "select" );
            var options = this.switchOptions[ onValue ];
            $select.attr( "name", this.prefix + options.name );
            $select.attr( "multiple", options.multiple );
            // Replace options regardless.
            var select2ed = this.$(".select2-container").length > 0;
            $select.html(""); // clear out select list
            _.each( options.options, function( option ) {
                var text = option[0];
                var value = option[1];
                var selected = option[2];
                $select.append($("<option />", {text: text, val: value, selected: selected}));
            });
            if( select2ed ) {
                // Without this select2 does not update options.
                $select.select2();
            }
        }
    });

    return {
        SwitchSelectView: SwitchSelectView
    };

});
