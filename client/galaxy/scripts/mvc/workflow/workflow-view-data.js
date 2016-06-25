define(['mvc/workflow/workflow-globals'], function( Globals ){

    var DataInputView = Backbone.View.extend( {
        className: "form-row dataRow input-data-row",

        initialize: function( options ){
            this.input = options.input;
            this.nodeView = options.nodeView;
            this.terminalElement = options.terminalElement;

            this.$el.attr( "name", this.input.name )
                    .html( this.input.label );

            if( ! options.skipResize ) {
                this.$el.css({  position:'absolute',
                                left: -1000,
                                top: -1000,
                                display:'none'});
            $('body').append(this.el);
                this.nodeView.updateMaxWidth( this.$el.outerWidth() );
                this.$el.css({ position:'',
                               left:'',
                               top:'',
                               display:'' });
                this.$el.remove();
            }
        }
    });

    var DataOutputView = Backbone.View.extend( {
        className: "form-row dataRow",

        initialize: function( options ) {
            this.output = options.output;
            this.terminalElement = options.terminalElement;
            this.nodeView = options.nodeView;

            var output = this.output;
            var label = output.name;
            var node = this.nodeView.node;

            var isInput = output.extensions.indexOf( 'input' ) >= 0 || output.extensions.indexOf( 'input_collection' ) >= 0;
            if ( ! isInput ) {
                label = label + " (" + output.extensions.join(", ") + ")";
            }
            this.$el.html( label )
            this.calloutView = null;
            if (['tool', 'subworkflow'].indexOf(node.type) >= 0){
                var calloutView = new OutputCalloutView( {
                    "label": label,
                    "output": output,
                    "node": node,
                });
                this.calloutView = calloutView;
                this.$el.append( calloutView.el );
                this.$el.hover( function() { calloutView.hoverImage() }, function() { calloutView.resetImage() } );
            }
            this.$el.css({  position:'absolute',
                            left: -1000,
                            top: -1000,
                            display:'none'});
            $('body').append( this.el );
            this.nodeView.updateMaxWidth( this.$el.outerWidth() + 17 );
            this.$el.css({ position:'',
                           left:'',
                           top:'',
                           display:'' })
                    .detach();
        },
        redrawWorkflowOutput: function() {
            if( this.calloutView ) {
                this.calloutView.resetImage();
            }
        }
    });

    var OutputCalloutView = Backbone.View.extend( {
        tagName: "div",

        initialize: function( options ) {
            this.label = options.label;
            this.node = options.node;
            this.output = options.output;

            var view = this;
            var node = this.node;
            this.$el
                .attr( "class", 'callout '+this.label )
                .css( { display: 'none' } )
                .append(
                    $("<div class='buttons'></div>").append(
                        $("<img/>").attr('src', Galaxy.root + 'static/images/fugue/asterisk-small-outline.png').click( function() {
                            var outputName = view.output.name;
                            if( node.isWorkflowOutput( outputName ) ) {
                                node.removeWorkflowOutput( outputName );
                                view.$('img').attr('src', Galaxy.root + 'static/images/fugue/asterisk-small-outline.png');
                            }else{
                                node.addWorkflowOutput( outputName );
                                view.$('img').attr('src', Galaxy.root + 'static/images/fugue/asterisk-small.png');
                            }
                            Globals.workflow.has_changes = true;
                            Globals.canvas_manager.draw_overview();
                        })))
                .tooltip({delay:500, title: "Mark dataset as a workflow output. All unmarked datasets will be hidden." });

            this.$el.css({
                    top: '50%',
                    margin:'-8px 0px 0px 0px',
                    right: 8
                });
            this.$el.show();
            this.resetImage();
        },

        resetImage: function() {
            if ( ! this.node.isWorkflowOutput( this.output.name ) ) {
                this.$('img').attr('src', Galaxy.root + 'static/images/fugue/asterisk-small-outline.png');
            } else{
                this.$('img').attr('src', Galaxy.root + 'static/images/fugue/asterisk-small.png');
            }
        },

        hoverImage: function() {
            this.$('img').attr('src', Galaxy.root + 'static/images/fugue/asterisk-small-yellow.png');
        }
    });

    return {
        DataInputView       : DataInputView,
        DataOutputView      : DataOutputView
    }
});
