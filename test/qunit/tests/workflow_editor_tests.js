/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
/* global Workflow, CanvasManager, InputTerminal, Connector, add_node */
define([
    "galaxy.workflow_editor.canvas",
    "jquery",
    "libs/bootstrap",  // Required by galaxy.workflow_editor.canvas
    "sinon-qunit"
], function(
    workflowEditor,
    $,
    bootstrap,
    sinon
){
    "use strict";

    // globals cosumed by workflow editor
    window.show_form_for_tool = sinon.spy();
    window.workflow = null;
    window.canvas_manager = null;


    QUnit.moduleStart(function() {
        window.populate_datatype_info({
            ext_to_class_name: {
                'txt': 'Text',
                'data': 'Data',
                'tabular': 'Tabular',
                'binary': 'Binary',
                'bam': 'Bam'
            },
            class_to_classes: {
                'Data': { 'Data': true },
                'Text': { 'Text': true, 'Data': true },
                'Tabular': { 'Tabular': true, 'Text': true, 'Data': true },
                'Binary': { 'Data': true, 'Binary': true },
                'Bam': { 'Data': true, 'Binary': true, 'Bam': true }
            }
        } );
    } );

    var with_canvas_container = function( f ) {
        var canvas_container = $("<div id='canvas-container'>");
        $("body").append( canvas_container );
        f( canvas_container );
        canvas_container.remove();
    };

    var with_workflow_global = function( f ) {
        var overview = $( "<div id='overview'><canvas id='overview-canvas'></canvas><div id='overview-viewport'></div></div>" );
        var canvas_viewport = $( "<div id='canvas-viewport'><div id='canvas-container'></div></div>" );

        $("body").append( overview, canvas_viewport );
        window.canvas_manager = new CanvasManager( canvas_viewport, overview );
        with_canvas_container( function( canvas_container ) {
            window.workflow = new Workflow( canvas_container );
            f( window.workflow );
            window.workflow = null;
        } );
        window.canvas_manager = null;
        overview.remove();
        canvas_viewport.remove();
    };

    module( "Input terminal model test", {
        setup: function( ) {
            this.node = new Node( {  } );
            this.input = { extensions: [ "txt" ], multiple: false };
            this.input_terminal = new InputTerminal( { input: this.input } );
            this.input_terminal.node = this.node;
        },
        multiple: function( ) {
            this.input.multiple = true;
            this.input_terminal.update( this.input );
        },
        test_connector: function( ) {
            var outputTerminal = new OutputTerminal( { datatypes: [ 'input' ] } );
            var inputTerminal = this.input_terminal;
            var connector;
            with_workflow_global( function() {
                connector = new Connector( outputTerminal, inputTerminal );
            } );
            return connector;
        },
        with_test_connector: function( f ) {
            this.test_connector( );
            f();
            this.reset_connectors();
        },
        reset_connectors: function( ) {
            this.input_terminal.connectors = [];
        },
        test_accept: function( other ) {
            other = other || { node: {}, datatypes: [ "txt" ] };
            if( ! other.mapOver ) {
                other.mapOver = function() { return NULL_COLLECTION_TYPE_DESCRIPTION; };
            }
            return this.input_terminal.canAccept( other );
        },
        pja_change_datatype_node: function( output_name, newtype ) {
            var pja = { action_type: "ChangeDatatypeAction", output_name: output_name, action_arguments: { newtype: newtype } };
            var otherNode = { post_job_actions: [ pja ] };
            return otherNode;
        }
    } );

    test( "test update", function() {
        deepEqual( this.input_terminal.datatypes, [ 'txt' ] );
        equal( this.input_terminal.multiple, false );

        this.input_terminal.update( { extensions: [ 'bam' ], multiple: true } );

        deepEqual( this.input_terminal.datatypes, [ 'bam' ] );
        equal( this.input_terminal.multiple, true );
    } );

    test( "test connect", function() {
        this.node.markChanged = sinon.spy();

        var connector = {};
        this.input_terminal.connect( connector );

        // Assert node markChanged called
        ok( this.node.markChanged.called );
        // Assert connectors updated
        ok( this.input_terminal.connectors[ 0 ] === connector );
    } );

    test( "test disconnect", function() {
        this.node.markChanged = sinon.spy();

        var connector = this.test_connector( );
        this.input_terminal.disconnect( connector );

        // Assert node markChanged called
        ok( this.node.markChanged.called );
        // Assert connectors updated
        equal( this.input_terminal.connectors.length, 0 );
    } );

    test( "test redraw", function() {
        var connector = this.test_connector(  );
        connector.redraw = sinon.spy();
        this.input_terminal.redraw();
        // Assert connectors were redrawn
        ok( connector.redraw.called );
    } );

    test( "test destroy", function() {
        var connector = this.test_connector();
        connector.destroy = sinon.spy();

        this.input_terminal.destroy();
        // Assert connectors were destroyed
        ok( connector.destroy.called );
    } );

    test( "can accept exact datatype", function() {
        var other = { node: {}, datatypes: [ "txt" ] }; // input also txt

        ok( this.test_accept() ) ;
    } );

    test( "can accept subclass datatype", function() {
        var other = { node: {}, datatypes: [ "tabular" ] }; // tabular subclass of input txt

        ok( this.test_accept() ) ;
    } );

    test( "cannot accept incorrect datatype", function() {
        var other = { node: {}, datatypes: [ "binary" ] }; // binary is not txt

        ok( ! this.test_accept( other ) );
    } );

    test( "can accept incorrect datatype if converted with PJA", function() {
        var otherNode = this.pja_change_datatype_node( "out1", "txt" );
        var other = { node: otherNode, datatypes: [ "binary" ], name: "out1" }; // Was binary but converted to txt

        ok( this.test_accept( other ) );
    } );

    test( "cannot accept incorrect datatype if converted with PJA to incompatible type", function() {
        var otherNode = this.pja_change_datatype_node( "out1", "bam" ); // bam's are not txt
        var other = { node: otherNode, datatypes: [ "binary" ], name: "out1" }; 

        ok( ! this.test_accept( other ) );
    } );

    test( "cannot accept incorrect datatype if some other output converted with PJA to compatible type", function() {
        var otherNode = this.pja_change_datatype_node( "out2", "txt" );
        var other = { node: otherNode, datatypes: [ "binary" ], name: "out1" };

        ok( ! this.test_accept( other ) );
    } );

    test( "can accept inputs", function() {
        // Other is data input module - always accept (currently - could be
        // more intelligent by looking at what else input is connected to.
        var other = { node: {}, datatypes: [ "input" ] };
        ok( this.test_accept( other ) );
    } );

    test( "cannot accept when already connected", function() {
        var self = this;
        // If other is subtype but already connected, cannot accept
        this.with_test_connector( function() {
            ok( ! self.test_accept() );
        } );
    } );

    test( "can accept already connected inputs if input is multiple", function() {
        var self = this;
        this.multiple();
        this.with_test_connector( function() {
            ok( self.test_accept() );
        } );
    } );

    test( "cannot accept already connected inputs if input is multiple but datatypes don't match", function() {
        var other = { node: {}, datatypes: [ "binary" ] }; // binary is not txt

        var self = this;
        this.multiple();
        this.with_test_connector( function() {
            ok( ! self.test_accept( other ) );
        } );
    } );

    test( "can accept list collection for multiple input parameters if datatypes match", function() {
        var self = this;
        this.multiple();
        ok( self.test_accept() );
    } );

    test( "can accept list collection for empty multiple inputs", function() {
        var other = { node: {}, datatypes: [ "tabular" ], mapOver: function() { return new CollectionTypeDescription( "list" ) } };
        var self = this;
        this.multiple();
        ok( self.test_accept( other ) );
    } );

    test( "cannot accept list collection for multiple input if collection already connected", function() {
        var other = { node: {}, datatypes: [ "tabular" ], mapOver: function() { return new CollectionTypeDescription( "list" ) } };
        var self = this;
        this.multiple();
        this.with_test_connector( function() {
            ok( ! self.test_accept( other ) );
        } );
    } );

    module( "Connector test", {

    } );

    test( "connects only if both valid handles", function() {
        var input = { connect: sinon.spy() };
        var output = { connect: sinon.spy() };
        new Connector( input, null );
        new Connector( null, output );
        // Not attempts to connect...
        ok( ! input.connect.called );
        ok( ! output.connect.called );

        new Connector( input, output );
        ok( input.connect.called );
        ok( output.connect.called );
    });

    test( "default attributes", function() {
        var input = { connect: sinon.spy() };
        var output = { connect: sinon.spy() };
        var connector = new Connector( input, output );

        equal( connector.dragging, false );
        equal( connector.canvas, null );
        equal( connector.inner_color, "#FFFFFF" );
        equal( connector.outer_color, "#D8B365" );
    } );

    test( "destroy", function() {
        var input = { connect: sinon.spy(), disconnect: sinon.spy() };
        var output = { connect: sinon.spy(), disconnect: sinon.spy() };
        var connector = new Connector( input, output );

        connector.destroy();
        ok( input.disconnect.called );
        ok( output.disconnect.called );
    } );

    test( "initial redraw", function() {
        with_canvas_container( function( canvas_container ) {
            var input = { connect: sinon.spy(), element: $("<div>"), isMappedOver: function() { return false; } };
            var output = { connect: sinon.spy(), element: $("<div>"), isMappedOver: function() { return false; } };
            var connector = new Connector( input, output );

            connector.redraw();
            // Ensure canvas gets set
            ok( connector.canvas );
            // Ensure it gest added to canvas container
            equal( canvas_container.children()[ 0 ], connector.canvas );
        } );
    } );

    module( "Node unit test", {
        setup: function() {
            this.input_terminal = { destroy: sinon.spy(), redraw: sinon.spy() };
            this.output_terminal = { destroy: sinon.spy(), redraw: sinon.spy() };
            this.element = $("<div><div class='toolFormBody'></div></div>");
            this.node = new Node( { element: this.element } );
            this.node.input_terminals.i1 = this.input_terminal;
            this.node.output_terminals.o1 = this.output_terminal;
        },
        $: function( selector ) {
            return $( this.node.element.find( selector ) );
        },
        expect_workflow_node_changed: function( f ) {
            var node = this.node;
            with_workflow_global( function( workflow ) {
                var node_changed_spy = sinon.spy( workflow, "node_changed" );
                f();
                ok( node_changed_spy.calledWith( node ) );
            } );
        },
        init_field_data_simple: function() {
            var data = {
                data_inputs: [ {name: "input1", extensions: [ "data" ] } ],
                data_outputs: [ {name: "output1", extensions: [ "data" ] } ],
            };
            this.node.init_field_data( data );
        },
        update_field_data_with_new_input: function() {
            var new_data = {
                data_inputs: [
                    { name: "input1", extensions: [ "data" ] },
                    { name: "extra_0|input1", extensions: [ "data" ] },
                ],
                data_outputs: [ {name: "output1", extensions: [ "data" ] } ],
                post_job_actions: "{}"
            };
            this.node.update_field_data( new_data );
        }
    } );

    test( "make active", function() {
        ok( ! this.element.hasClass( "toolForm-active" ) );
        this.node.make_active();
        ok( this.element.hasClass( "toolForm-active" ) );
    } );

    test( "destroy", function() {
        var test = this;
        with_workflow_global( function( workflow ) {
            var remove_node_spy = sinon.spy( workflow, "remove_node" );
            test.node.destroy();
            ok( test.input_terminal.destroy.called );
            ok( test.output_terminal.destroy.called );
            ok( remove_node_spy.calledWith( test.node ) );
        } );
    } );

    test( "error", function() {
        // Test body of toolFormBody div updated and workflow notified of change.
        var test = this;
        this.expect_workflow_node_changed( function() {
            test.node.error( "TOOL ERROR" );
            equal( $( test.$(".toolFormBody").children()[ 0 ] ).html(), "TOOL ERROR" );
        } );
    } );

    test( "init_field_data properties", function() {
        var node = this.node;
        this.expect_workflow_node_changed( function( ) {
            var data = {
                data_inputs: [],
                data_outputs: [],
                type: "tool",
                name: "cat1",
                form_html: "<form>",
                tool_state: "ok",
                tool_errors: false,
                tooltip: "tool tooltip",
                annotation: "tool annotation",
                workflow_outputs: [ "out1" ],
            };
            node.init_field_data( data );
            equal( node.type, "tool" );
            equal( node.name, "cat1" );
            equal( node.form_html, "<form>" );
            equal( node.tool_state, "ok" );
            equal( node.tooltip, "tool tooltip" );
            equal( node.annotation, "tool annotation" );
            deepEqual( node.post_job_actions, {} );
            deepEqual( node.workflow_outputs, [ "out1" ] );
        } );
    } );

    test( "init_field_data data", function() {
        var test = this;
        this.expect_workflow_node_changed( function( ) {
            // pre-init not tool form body...
            equal( test.$( ".output-terminal" ).length, 0 );
            equal( test.$( ".input-terminal" ).length, 0 );
            equal( test.$( ".rule" ).length, 0 );

            test.init_field_data_simple();

            // After init tool form should have three "rows"/divs - , inputs div, one output, and rule...
            equal( test.$( ".output-terminal" ).length, 1 );
            equal( test.$( ".input-terminal" ).length, 1 );
            equal( test.$( ".rule" ).length, 1 );

            equal( test.$( ".toolFormBody" ).children().length, 3 );
        } );
    } );

    test( "update_field_data updated data inputs and outputs", function() {
        var test = this;
        this.expect_workflow_node_changed( function( ) {
            // Call init with one input and output.
            test.init_field_data_simple();

            test.update_field_data_with_new_input();

            // Now there are 2 inputs...
            equal( test.$( ".input-terminal" ).length, 2 );
            equal( test.$( ".output-terminal" ).length, 1 );
            equal( test.$( ".rule" ).length, 1 );
        } );
    } );

    test( "update_field_data preserves connectors", function() {
        var test = this;
        var node = this.node;
        this.expect_workflow_node_changed( function( ) {
            // Call init with one input and output.
            test.init_field_data_simple();

            var connector = new Connector();
            var old_input_terminal = node.input_terminals.input1;
            old_input_terminal.connectors.push( connector );

            // Update node, make sure connector still the same...
            test.update_field_data_with_new_input();
            var new_input_terminal = node.input_terminals.input1;
            equal( connector, new_input_terminal.connectors[ 0 ] );

            // Update a second time, make sure connector still the same...
            test.update_field_data_with_new_input();
            new_input_terminal = node.input_terminals.input1;
            equal( connector, new_input_terminal.connectors[ 0 ] );
        } );
    } );

    test( "update_field_data destroys old terminals", function() {
        var test = this;
        var node = this.node;
        this.expect_workflow_node_changed( function( ) {
            var data = {
                data_inputs: [ { name: "input1", extensions: [ "data" ] },
                               { name: "willDisappear", extensions: [ "data" ] } ],
                data_outputs: [ {name: "output1", extensions: [ "data" ] } ],
            };
            node.init_field_data( data );

            var old_input_terminal = node.input_terminals.willDisappear;
            var destroy_spy = sinon.spy( old_input_terminal, "destroy" );
            // Update
            test.update_field_data_with_new_input();

            ok( destroy_spy.called );
        } );
    } );

    module( "add_node" );

    test( "node added to workflow", function() {
        with_workflow_global( function( workflow ) {
            var add_node_spy = sinon.spy( workflow, "add_node" );
            var node = add_node( "tool", "Cat Files", "cat1" );
            ok( add_node_spy.calledWith( node ) );
        } );
    } );

    /* global NodeView */
    module( "Node view ", {
       setup: function() {
            this.set_for_node( { input_terminals: {}, output_terminals: {}, markChanged: function() {}, terminalMapping: { disableMapOver: function() {} } } );
        },
        set_for_node: function( node ) {
            var element = $("<div><div class='toolFormBody'></div></div>");
            this.view = new NodeView( { node: node, el: element[ 0 ] } );
        },
        connectAttachedTerminal: function( inputType, outputType ) {
            this.view.addDataInput( { name: "TestName", extensions: [ inputType ] } );
            var terminal = this.view.node.input_terminals[ "TestName" ];

            var outputTerminal = new OutputTerminal( { name: "TestOuptut", datatypes: [ outputType ] } );
            outputTerminal.node = { markChanged: function() {}, post_job_actions: [], hasMappedOverInputTerminals: function() { return false; }, hasConnectedOutputTerminals: function() { return true; } };
            outputTerminal.terminalMapping = { disableMapOver: function() {}, mapOver: NULL_COLLECTION_TYPE_DESCRIPTION }; 
            var c = new Connector( outputTerminal, terminal );

            return c;
        },
        connectAttachedMultiInputTerminal: function( inputType, outputType ) {
            this.view.addDataInput( { name: "TestName", extensions: [ inputType ], multiple: true } );
            var terminal = this.view.node.input_terminals[ "TestName" ];

            var outputTerminal = new OutputTerminal( { name: "TestOuptut", datatypes: [ "txt" ] } );
            outputTerminal.node = { markChanged: function() {}, post_job_actions: [], hasMappedOverInputTerminals: function() { return false; }, hasConnectedOutputTerminals: function() { return true; } };
            outputTerminal.terminalMapping = { disableMapOver: function() {}, mapOver: new CollectionTypeDescription( "list" ) };
            var c = new Connector( outputTerminal, terminal );

            return c;
        },
        connectAttachedMappedOutput: function( ) {
            this.view.addDataInput( { name: "TestName", extensions: [ "txt" ], input_type: "dataset_collection" } );
            var terminal = this.view.node.input_terminals[ "TestName" ];

            var outputTerminal = new OutputTerminal( { name: "TestOuptut", datatypes: [ "txt" ] } );
            outputTerminal.node = { markChanged: function() {}, post_job_actions: [], hasMappedOverInputTerminals: function() { return false; }, hasConnectedOutputTerminals: function() { return true; } };
            outputTerminal.terminalMapping = { disableMapOver: function() {}, mapOver: new CollectionTypeDescription( "list" ) }; 
            var c = new Connector( outputTerminal, terminal );

            return c;
        }
    } );

    test( "tool error styling", function() {
        this.set_for_node( { tool_errors: false } );
        this.view.render();
        ok( ! this.view.$el.hasClass( "tool-node-error" ) );
        this.set_for_node( { tool_errors: true } );
        this.view.render();
        ok( this.view.$el.hasClass( "tool-node-error" ) );
    } );

    test( "rendering correct width", function() {
        // Default width is 150
        this.view.render();
        equal( this.view.$el.width(), 150 );

        // If any data rows are greater, it will update
        this.view.updateMaxWidth( 200 );
        this.view.render();
        equal( this.view.$el.width(), 200 );

        // However 250 is the maximum width of node
        this.view.updateMaxWidth( 300 );
        this.view.render();
        equal( this.view.$el.width(), 250 );

    } );

    test( "replacing terminal on data input update preserves connections", function() {
        var connector = this.connectAttachedTerminal( "txt", "txt" );
        var newElement = $("<div class='inputs'></div>");
        this.view.addDataInput( { name: "TestName", extensions: ["txt"] }, newElement );
        var terminal = newElement.find(".input-terminal")[ 0 ].terminal;
        ok( connector.handle2 === terminal );
    } );

    test( "replacing terminal on data multiple input update preserves collection connections", function() {
        var connector = this.connectAttachedMultiInputTerminal( "txt", "txt" );
        var connector_destroy_spy = sinon.spy( connector, "destroy" );
        var newElement = $("<div class='inputs'></div>");
        this.view.addDataInput( { name: "TestName", extensions: ["txt"], multiple: true }, newElement );
        ok( ! connector_destroy_spy.called );
    } );

    test( "replacing mapped terminal on data collection input update preserves connections", function() {
        var connector = this.connectAttachedMappedOutput();
        var newElement = $("<div class='inputs'></div>");
        this.view.addDataInput( { name: "TestName", extensions: ["txt"], input_type: "dataset_collection" }, newElement );
        var terminal = newElement.find(".input-terminal")[ 0 ].terminal;
        ok( connector.handle2 === terminal );
    } );

    test( "replacing terminal on data input destroys invalid connections", function() {
        var connector = this.connectAttachedTerminal( "txt", "txt" );
        var newElement = $("<div class='inputs'></div>");
        var connector_destroy_spy = sinon.spy( connector, "destroy" );
        // Replacing input with same name - but now of type bam should destroy connection.
        this.view.addDataInput( { name: "TestName", extensions: ["bam"] }, newElement );
        var terminal = newElement.find(".input-terminal")[ 0 ].terminal;
        ok( connector_destroy_spy.called );
    } );

    test( "replacing terminal on data input with collection changes mapping view type", function() {
        var connector = this.connectAttachedTerminal( "txt", "txt" );
        var newElement = $("<div class='inputs'></div>");
        var connector_destroy_spy = sinon.spy( connector, "destroy" );
        this.view.addDataInput( { name: "TestName", extensions: ["txt"], input_type: "dataset_collection" }, newElement );
        // Input type changed to dataset_collection - old connections are reset.
        // Would be nice to preserve these connections and make them map over.
        var terminal = newElement.find(".input-terminal")[ 0 ].terminal;
        ok( connector_destroy_spy.called );
    } );

    test( "replacing terminal on data collection input with simple input changes mapping view type", function() {
        var connector = this.connectAttachedMappedOutput();
        var newElement = $("<div class='inputs'></div>");
        var connector_destroy_spy = sinon.spy( connector, "destroy" );
        this.view.addDataInput( { name: "TestName", extensions: ["txt"], input_type: "dataset" }, newElement );
        var terminal = newElement.find(".input-terminal")[ 0 ].terminal;
        ok( connector_destroy_spy.called );
    } );

    /* global InputTerminalView */
    module( "Input terminal view", {
        setup: function() {
            this.node = { input_terminals: [] };
            this.input = { name: "i1", extensions: "txt", multiple: false };
            this.view = new InputTerminalView( {
                node: this.node,
                input: this.input,
            });
        }
    } );

    test( "terminal added to node", function() {
        ok( this.node.input_terminals.i1 );
        equal( this.node.input_terminals.i1.datatypes, [ "txt" ] );
        equal( this.node.input_terminals.i1.multiple, false );
    } );

    test( "terminal element", function() {
        var el = this.view.el;
        equal( el.tagName, "DIV" );
        equal( el.className, "terminal input-terminal");
    } );

    // TODO: Test binding... not sure how to do that exactly..

    /* global OutputTerminalView */
    module( "Output terminal view", {
        setup: function() {
            this.node = { output_terminals: [] };
            this.output = { name: "o1", extensions: "txt" };
            this.view = new OutputTerminalView( {
                node: this.node,
                output: this.output,
            });
        }
    } );

    test( "terminal added to node", function() {
        ok( this.node.output_terminals.o1 );
        equal( this.node.output_terminals.o1.datatypes, [ "txt" ] );
    } );

    test( "terminal element", function() {
        var el = this.view.el;
        equal( el.tagName, "DIV" );
        equal( el.className, "terminal output-terminal");
    } );

    // TODO: Test bindings

    module( "CollectionTypeDescription", {
        listType: function() {
            return new CollectionTypeDescription( "list" );
        },
        pairedType: function() {
            return new CollectionTypeDescription( "paired" );
        },
        pairedListType: function() {
            return new CollectionTypeDescription( "list:paired" );            
        }
    } );

    test( "canMatch", function() {
        ok( this.listType().canMatch( this.listType() ) );
        ok( ! this.listType().canMatch( this.pairedType() ) );
        ok( ! this.listType().canMatch( this.pairedListType() ) );
    } );

    test( "canMatch special types", function() {
        ok( this.listType().canMatch( ANY_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ANY_COLLECTION_TYPE_DESCRIPTION.canMatch( this.pairedListType() ) );

        ok( ! this.listType().canMatch( NULL_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! NULL_COLLECTION_TYPE_DESCRIPTION.canMatch( this.pairedListType() ) );
    } );

    test( "canMapOver", function() {
        ok( ! this.listType().canMapOver( this.listType() ) );
        ok( ! this.listType().canMapOver( this.pairedType() ) );
        ok( this.pairedListType().canMapOver( this.pairedType() ) );
        ok( ! this.listType().canMapOver( this.pairedListType() ) );
    } );

    test( "canMapOver special types", function() {
        ok( ! this.listType().canMapOver( NULL_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! NULL_COLLECTION_TYPE_DESCRIPTION.canMapOver( this.pairedListType() ) );

        // Following two should be able to be relaxed someday maybe - but the
        // tracking gets tricky I think. For now mapping only works for explicitly
        // defined collection types.
        ok( ! this.listType().canMapOver( ANY_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! ANY_COLLECTION_TYPE_DESCRIPTION.canMapOver( this.pairedListType() ) );
    } );

    test( "append", function( other ) {
        var appendedType = this.listType().append( this.pairedType() );
        equal( appendedType.collectionType, "list:paired" );
    } );

    test( "isCollection", function() {
        ok( this.listType().isCollection );
        ok( ANY_COLLECTION_TYPE_DESCRIPTION.isCollection );
        ok( ! NULL_COLLECTION_TYPE_DESCRIPTION.isCollection );
    } );

    test( "equal", function() {
        ok( ! this.listType().equal( this.pairedType() ) );
        ok( this.listType().equal( this.listType() ) );

        ok( ANY_COLLECTION_TYPE_DESCRIPTION.equal( ANY_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! ANY_COLLECTION_TYPE_DESCRIPTION.equal( NULL_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! ANY_COLLECTION_TYPE_DESCRIPTION.equal( this.pairedType() ) );
        ok( ! this.pairedType().equal( ANY_COLLECTION_TYPE_DESCRIPTION ) );

        ok( NULL_COLLECTION_TYPE_DESCRIPTION.equal( NULL_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! NULL_COLLECTION_TYPE_DESCRIPTION.equal( ANY_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! NULL_COLLECTION_TYPE_DESCRIPTION.equal( this.listType() ) );
        ok( ! this.listType().equal( NULL_COLLECTION_TYPE_DESCRIPTION ) );

    } );

    module( "TerminalMapping", {

    } );

    test( "default constructor", function() {
        var terminal = {};
        var mapping = new TerminalMapping( { terminal: terminal } );
        ok( terminal.terminalMapping === mapping );
        ok( mapping.mapOver === NULL_COLLECTION_TYPE_DESCRIPTION );
    } );

    test( "constructing with mapOver", function() {
        var terminal = {};
        var mapping = new TerminalMapping( { terminal: terminal, mapOver: new CollectionTypeDescription( "list" ) } );
        ok( mapping.mapOver.collectionType == "list" );
    } );

    test( "disableMapOver", function() {
        var terminal = {};
        var mapping = new TerminalMapping( { terminal: terminal, mapOver: new CollectionTypeDescription( "list" ) } );
        var changeSpy = sinon.spy();
        mapping.bind( "change", changeSpy );
        mapping.disableMapOver();
        ok( mapping.mapOver === NULL_COLLECTION_TYPE_DESCRIPTION );
        ok( changeSpy.called );
    } );

    module( "terminal mapping logic", {
        newInputTerminal: function( mapOver, input, node ) {
            input = input || {};
            node = node || this.newNode();
            if( ! ( 'extensions' in input ) ) {
                input[ 'extensions'] = [ 'data' ];
            }
            var inputEl = $("<div>")[ 0 ];
            var inputTerminal = new InputTerminal( { element: inputEl, input: input } );
            var inputTerminalMapping = new InputTerminalMapping( { terminal: inputTerminal } );
            inputTerminal.node = node;
            if( mapOver ) {
                inputTerminal.setMapOver( new CollectionTypeDescription( mapOver ) );
            }
            return inputTerminal;
        },
        newInputCollectionTerminal: function( input, node ) {
            input = input || {};
            node = node || this.newNode();
            if( ! ( 'extensions' in input ) ) {
                input[ 'extensions'] = [ 'data' ];
            }
            var inputEl = $("<div>")[ 0 ];
            var inputTerminal = new InputCollectionTerminal( { element: inputEl, input: input } );
            var inputTerminalMapping = new InputCollectionTerminalMapping( { terminal: inputTerminal } );
            inputTerminal.node = node;
            return inputTerminal;
        },
        newOutputTerminal: function( mapOver, output, node ) {
            output = output || {};
            node = node || this.newNode();
            if( ! ( 'extensions' in output ) ) {
                output[ 'extensions'] = [ 'data' ];
            }
            var outputEl = $("<div>")[ 0 ];
            var outputTerminal = new OutputTerminal( { element: outputEl, datatypes: output.extensions } );
            var outputTerminalMapping = new OutputTerminalMapping( { terminal: outputTerminal } );
            outputTerminal.node = node;
            if( mapOver ) {
                outputTerminal.setMapOver( new CollectionTypeDescription( mapOver ) );
            }
            return outputTerminal;
        },
        newNode: function( ) {
            var nodeEl = $("<div>")[ 0 ];
            var node = new Node( { element: nodeEl } );
            return node;
        },
        addOutput: function( terminal, connected ) {
            var self = this;
            var connectedOutput = this.newOutputTerminal();
            var node = terminal.node;
            if( connected ) {
                with_workflow_global( function() {
                    var inputTerminal = self.newInputTerminal();
                    new Connector( inputTerminal, connectedOutput );
                } );
            }
            this._addTerminalTo( connectedOutput, node.output_terminals );
            return connectedOutput;
        },
        addConnectedOutput: function( terminal ) {
            return this.addOutput( terminal, true );
        },
        addConnectedInput: function( terminal ) {
            var self = this;
            var connectedInput = this.newInputTerminal();
            var node = terminal.node;
            with_workflow_global( function() {
                var outputTerminal = self.newOutputTerminal();
                new Connector( connectedInput, outputTerminal );
            } );
            this._addTerminalTo( connectedInput, node.input_terminals );
            return connectedInput;
        },
        _addTerminalTo: function( terminal, terminals ) {
            var name = "other";
            while( name in terminals ) {
                name += "_";
            }
            terminals[ name ] = terminal;
        },
        verifyNotAttachable: function( inputTerminal, output ) {
            var outputTerminal;
            var outputTerminal;
            if( typeof( output ) == "string" ) {
                // Just given a collection type... create terminal out of it.
                outputTerminal = this.newOutputTerminal( output );
            } else {
                outputTerminal = output;
            }

            ok( ! inputTerminal.attachable( outputTerminal ) );
        },
        verifyAttachable: function( inputTerminal, output ) {
            var outputTerminal;
            if( typeof( output ) == "string" ) {
                // Just given a collection type... create terminal out of it.
                outputTerminal = this.newOutputTerminal( output );
            } else {
                outputTerminal = output;
            }

            ok( inputTerminal.attachable( outputTerminal ) );
            
            // Go further... make sure datatypes are being enforced
            inputTerminal.datatypes = [ "bam" ];
            outputTerminal.datatypes = [ "txt" ];
            ok( ! inputTerminal.attachable( outputTerminal ) );
        },
        verifyMappedOver: function( terminal ) {
            ok( terminal.terminalMapping.mapOver.isCollection );
        },
        verifyNotMappedOver: function( terminal ) {
            ok( ! terminal.terminalMapping.mapOver.isCollection );
        },
    } );

    test( "unconstrained input can be mapped over", function() {
        var inputTerminal1 = this.newInputTerminal();
        this.verifyAttachable( inputTerminal1, "list" );
    } );

    test( "unmapped input can be mapped over if matching connected input terminals map type", function() {
        var inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput( inputTerminal1 );
        var connectedInput2 = this.addConnectedInput( inputTerminal1 );
        connectedInput2.setMapOver( new CollectionTypeDescription( "list") );
        this.verifyAttachable( inputTerminal1, "list" );
    } );

    test( "unmapped input cannot be mapped over if not matching connected input terminals map type", function() {
        var inputTerminal1 = this.newInputTerminal();
        var connectedInput = this.addConnectedInput( inputTerminal1 );
        connectedInput.setMapOver( new CollectionTypeDescription( "paired" ) );
        this.verifyNotAttachable( inputTerminal1, "list" );
    } );

    test( "unmapped input with unmapped, connected outputs cannot be mapped over", function() {
        // It would invalidate the connections - someday maybe we could try to
        // recursively map over everything down the DAG - it would be expensive
        // to check that though.
        var inputTerminal1 = this.newInputTerminal();
        this.addConnectedOutput( inputTerminal1 );
        this.verifyNotAttachable( inputTerminal1, "list" );
    } );

    test( "unmapped input with connected mapped outputs can be mapped over if matching", function() {
        // It would invalidate the connections - someday maybe we could try to
        // recursively map over everything down the DAG - it would be expensive
        // to check that though.
        var inputTerminal1 = this.newInputTerminal();
        var connectedOutput = this.addConnectedOutput( inputTerminal1 );
        connectedOutput.setMapOver( new CollectionTypeDescription( "list" ) );
        this.verifyAttachable( inputTerminal1, "list" );
    } );

    test( "unmapped input with connected mapped outputs cannot be mapped over if mapover not matching", function() {
        // It would invalidate the connections - someday maybe we could try to
        // recursively map over everything down the DAG - it would be expensive
        // to check that though.
        var inputTerminal1 = this.newInputTerminal();
        var connectedOutput = this.addConnectedOutput( inputTerminal1 );
        connectedOutput.setMapOver( new CollectionTypeDescription( "paired" ) );
        this.verifyNotAttachable( inputTerminal1, "list" );
    } );

    test( "explicitly constrained input can not be mapped over by incompatible collection type", function() {
        var inputTerminal1 = this.newInputTerminal();
        inputTerminal1.setMapOver( new CollectionTypeDescription( "paired" ) );
        this.verifyNotAttachable( inputTerminal1, "list" );
    } );

    test( "explicitly constrained input can be mapped over by compatible collection type", function() {
        var inputTerminal1 = this.newInputTerminal();
        inputTerminal1.setMapOver( new CollectionTypeDescription( "list" ) );
        this.verifyAttachable( inputTerminal1, "list" );
    } );

    test( "unconstrained collection input can be mapped over", function() {
        var inputTerminal1 = this.newInputCollectionTerminal( { collection_type: "paired" } );
        this.verifyAttachable( inputTerminal1, "list:paired" );
    } );

    test( "unconstrained collection input cannot be mapped over by incompatible type", function() {
        var inputTerminal1 = this.newInputCollectionTerminal( { collection_type: "list" } ); // Would need to be paired...
        this.verifyNotAttachable( inputTerminal1, "list:paired" );
    } );

    test( "explicitly mapped over collection input can be attached by explicit mapping", function() {
        var inputTerminal1 = this.newInputCollectionTerminal( { collection_type: "paired" } );
        inputTerminal1.setMapOver( new CollectionTypeDescription( "list" ) );
        this.verifyAttachable( inputTerminal1, "list:paired" );
    } );

    test( "explicitly mapped over collection input can be attached by explicit mapping", function() {
        var inputTerminal1 = this.newInputCollectionTerminal( { collection_type: "list:paired" } );
        inputTerminal1.setMapOver( new CollectionTypeDescription( "list" ) );
        // effectively input is list:list:paired so shouldn't be able to attach
        this.verifyNotAttachable( inputTerminal1, "list:paired" );
    } );

    test( "unconnected multiple inputs can be connected to rank 1 collections", function() {
        var inputTerminal1 = this.newInputTerminal( null, { multiple: true } );
        this.verifyAttachable( inputTerminal1, "list" );
    } );

    test( "multiple input attachable by collections", function() {
        var inputTerminal1 = this.newInputTerminal( null, { multiple: true } );
        var connectedInput1 = this.addConnectedInput( inputTerminal1 );
        this.addConnectedOutput( connectedInput1 );
        this.verifyAttachable( inputTerminal1, "list" );
    } );

    test( "unconnected multiple inputs cannot be connected to rank > 1 collections (yet...)", function() {
        var inputTerminal1 = this.newInputTerminal( null, { multiple: true } );
        this.verifyNotAttachable( inputTerminal1, "list:paired" );
    } );

    test( "resetMappingIfNeeded does nothing if not mapped", function() {
        var inputTerminal1 = this.newInputTerminal();
        inputTerminal1.resetMappingIfNeeded();
        this.verifyNotMappedOver( inputTerminal1 );
    } );

    test( "resetMappingIfNeeded resets unconstrained input", function() {
        var inputTerminal1 = this.newInputTerminal( "list" );
        this.verifyMappedOver( inputTerminal1 );
        inputTerminal1.resetMappingIfNeeded();
        this.verifyNotMappedOver( inputTerminal1 );
    } );

    test( "resetMappingIfNeeded does not reset if connected output depends on being mapped", function() {
        var inputTerminal1 = this.newInputTerminal( "list" );
        var connectedOutput = this.addConnectedOutput( inputTerminal1 );
        connectedOutput.setMapOver( new CollectionTypeDescription( "list" ) );
        inputTerminal1.resetMappingIfNeeded();
        this.verifyMappedOver( inputTerminal1 );
    } );

    test( "resetMappingIfNeeded resets if node outputs are not connected to anything", function() {
        var inputTerminal1 = this.newInputTerminal( "list" );
        var output = this.addOutput( inputTerminal1 );
        output.setMapOver( new CollectionTypeDescription( "list" ) );
        inputTerminal1.resetMappingIfNeeded();
        this.verifyNotMappedOver( inputTerminal1 );
    } );

    test( "resetMappingIfNeeded an input resets node outputs if they not connected to anything", function() {
        var inputTerminal1 = this.newInputTerminal( "list" );
        var output = this.addOutput( inputTerminal1 );
        output.setMapOver( new CollectionTypeDescription( "list" ) );
        inputTerminal1.resetMappingIfNeeded();
        this.verifyNotMappedOver( output );
    } );

    test( "resetMappingIfNeeded resets if not last mapped over input", function() {
        // Idea here is that other nodes are forcing output to still be mapped
        // over so don't need to disconnect output nodes.
        var inputTerminal1 = this.newInputTerminal( "list" );
        var connectedInput1 = this.addConnectedInput( inputTerminal1 );
        connectedInput1.setMapOver( new CollectionTypeDescription( "list" ) );
        var connectedOutput = this.addConnectedOutput( inputTerminal1 );
        connectedOutput.setMapOver( new CollectionTypeDescription( "list" ) );
        inputTerminal1.resetMappingIfNeeded();
        // inputTerminal1 can be reset because connectedInput1
        // is still forcing connectedOutput to be mapped over,
        // so verify inputTerminal1 is rest and connectedInput1
        // and connectedOutput are untouched.
        this.verifyNotMappedOver( inputTerminal1 );
        this.verifyMappedOver( connectedInput1 );
        this.verifyMappedOver( connectedOutput );
    } );

});