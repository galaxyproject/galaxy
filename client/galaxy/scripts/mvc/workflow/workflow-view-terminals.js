define(['mvc/workflow/workflow-globals', 'mvc/workflow/workflow-terminals',
        'mvc/workflow/workflow-connector'], function( Globals, Terminals, Connector ) {

    var TerminalMappingView = Backbone.View.extend( {
        tagName: "div",
        className: "fa-icon-button fa fa-folder-o",
        initialize: function( options ) {
            var mapText = "Run tool in parallel over collection";
            this.$el.tooltip( {delay: 500, title: mapText } );
            this.model.bind( "change", _.bind( this.render, this ) );
        },
        render: function() {
            if( this.model.mapOver.isCollection ) {
                this.$el.show();
            } else {
                this.$el.hide();
            }
        }
    });

    var InputTerminalMappingView = TerminalMappingView.extend( {
        events: {
            "click": "onClick",
            "mouseenter": "onMouseEnter",
            "mouseleave": "onMouseLeave",
        },
        onMouseEnter: function( e ) {
            var model = this.model;
            if( ! model.terminal.connected() && model.mapOver.isCollection ) {
                this.$el.css( "color", "red" );
            }
        },
        onMouseLeave: function( e ) {
            this.$el.css( "color", "black" );
        },
        onClick: function( e ) {
            var model = this.model;
            if( ! model.terminal.connected() && model.mapOver.isCollection ) {
                // TODO: Consider prompting...
                model.terminal.resetMapping();
            }
        }
    });

    var TerminalView = Backbone.View.extend( {
        setupMappingView: function( terminal ) {
            var terminalMapping = new this.terminalMappingClass( { terminal: terminal } );
            var terminalMappingView = new this.terminalMappingViewClass( { model: terminalMapping } );
            terminalMappingView.render();
            terminal.terminalMappingView = terminalMappingView;
            this.terminalMappingView = terminalMappingView;
        },
        terminalElements: function() {
            if( this.terminalMappingView ) {
                return [ this.terminalMappingView.el, this.el ];
            } else{
                return [ this.el ];
            }
        }
    });

    var BaseInputTerminalView = TerminalView.extend( {
        className: "terminal input-terminal",
        initialize: function( options ) {
            var node = options.node;
            var input = options.input;
            var name = input.name;
            var terminal = this.terminalForInput( input );
            if( ! terminal.multiple ) {
                this.setupMappingView( terminal );
            }
            this.el.terminal = terminal;
            terminal.node = node;
            terminal.name = name;
            node.input_terminals[name] = terminal;
        },
        events: {
            "dropinit": "onDropInit",
            "dropstart": "onDropStart",
            "dropend": "onDropEnd",
            "drop": "onDrop",
            "hover": "onHover",
        },
        onDropInit: function( e, d ) {
            var terminal = this.el.terminal;
            // Accept a dragable if it is an output terminal and has a
            // compatible type
            return $(d.drag).hasClass( "output-terminal" ) && terminal.canAccept( d.drag.terminal );
        },
        onDropStart: function( e, d  ) {
            if (d.proxy.terminal) { 
                d.proxy.terminal.connectors[0].inner_color = "#BBFFBB";
            }
        },
        onDropEnd: function ( e, d ) {
            if (d.proxy.terminal) { 
                d.proxy.terminal.connectors[0].inner_color = "#FFFFFF";
            }
        },
        onDrop: function( e, d ) {
            var terminal = this.el.terminal;        
            new Connector( d.drag.terminal, terminal ).redraw();
        },
        onHover: function() {
            var element = this.el;
            var terminal = element.terminal;
            // If connected, create a popup to allow disconnection
            if ( terminal.connectors.length > 0 ) {
                // Create callout
                var t = $("<div class='callout'></div>")
                    .css( { display: 'none' } )
                    .appendTo( "body" )
                    .append(
                        $("<div class='button'></div>").append(
                            $("<div/>").addClass("fa-icon-button fa fa-times").click( function() {
                                $.each( terminal.connectors, function( _, x ) {
                                    if (x) {
                                        x.destroy();
                                    }
                                });
                                t.remove();
                            })))
                    .bind( "mouseleave", function() {
                        $(this).remove();
                    });
                // Position it and show
                t.css({
                        top: $(element).offset().top - 2,
                        left: $(element).offset().left - t.width(),
                        'padding-right': $(element).width()
                    }).show();
            }
        }
    });

    var InputTerminalView = BaseInputTerminalView.extend( {
        terminalMappingClass: Terminals.TerminalMapping,
        terminalMappingViewClass: InputTerminalMappingView,
        terminalForInput: function( input ) {
            return new Terminals.InputTerminal( { element: this.el, input: input } );
        }
    });

    var InputCollectionTerminalView = BaseInputTerminalView.extend( {
        terminalMappingClass: Terminals.TerminalMapping,
        terminalMappingViewClass: InputTerminalMappingView,
        terminalForInput: function( input ) {
            return new Terminals.InputCollectionTerminal( { element: this.el, input: input } );
        }
    });

    var BaseOutputTerminalView = TerminalView.extend( {
        className: "terminal output-terminal",
        initialize: function( options ) {
            var node = options.node;
            var output = options.output;
            var name = output.name;
            var terminal = this.terminalForOutput( output );
            this.setupMappingView( terminal );
            this.el.terminal = terminal;
            terminal.node = node;
            terminal.name = name;
            node.output_terminals[name] = terminal;
        },
        events: {
            "drag": "onDrag",
            "dragstart": "onDragStart",
            "dragend": "onDragEnd",
        },
        onDrag: function ( e, d ) {
            var onmove = function() {
                var po = $(d.proxy).offsetParent().offset(),
                    x = d.offsetX - po.left,
                    y = d.offsetY - po.top;
                $(d.proxy).css( { left: x, top: y } );
                d.proxy.terminal.redraw();
                // FIXME: global
                Globals.canvas_manager.update_viewport_overlay();
            };
            onmove();
            $("#canvas-container").get(0).scroll_panel.test( e, onmove );
        },
        onDragStart: function( e, d ) { 
            $( d.available ).addClass( "input-terminal-active" );
            // Save PJAs in the case of change datatype actions.
            Globals.workflow.check_changes_in_active_form(); 
            // Drag proxy div
            var h = $( '<div class="drag-terminal" style="position: absolute;"></div>' )
                .appendTo( "#canvas-container" ).get(0);
            // Terminal and connection to display noodle while dragging
            h.terminal = new Terminals.OutputTerminal( { element: h } );
            var c = new Connector();
            c.dragging = true;
            c.connect( this.el.terminal, h.terminal );
            return h;
        },
        onDragEnd: function ( e, d ) {
            var connector = d.proxy.terminal.connectors[0];
            // check_changes_in_active_form may change the state and cause a
            // the connection to have already been destroyed. There must be better
            // ways to handle this but the following check fixes some serious GUI
            // bugs for now.
            if(connector) {
                connector.destroy();
            }
            $(d.proxy).remove();
            $( d.available ).removeClass( "input-terminal-active" );
            $("#canvas-container").get(0).scroll_panel.stop();
        }
    });

    var OutputTerminalView = BaseOutputTerminalView.extend( {
        terminalMappingClass: Terminals.TerminalMapping,
        terminalMappingViewClass: TerminalMappingView,
        terminalForOutput: function( output ) {
            var type = output.extensions;
            var terminal = new Terminals.OutputTerminal( { element: this.el, datatypes: type } );
            return terminal;
        }
    });

    var OutputCollectionTerminalView = BaseOutputTerminalView.extend( {
        terminalMappingClass: Terminals.TerminalMapping,
        terminalMappingViewClass: TerminalMappingView,
        terminalForOutput: function( output ) {
            var collection_type = output.collection_type;
            var terminal = new Terminals.OutputCollectionTerminal( { element: this.el, collection_type: collection_type, datatypes: output.extensions } );
            return terminal;
        }
    });

    return {
        InputTerminalView               : InputTerminalView,
        OutputTerminalView              : OutputTerminalView,
        InputCollectionTerminalView     : InputCollectionTerminalView,
        OutputCollectionTerminalView    : OutputCollectionTerminalView
    }
});