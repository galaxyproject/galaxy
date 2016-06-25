/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
define([
    "sinon-qunit",
    "test-app",
    'utils/utils',
    "mvc/workflow/workflow-view",
    "mvc/workflow/workflow-node",
    "mvc/workflow/workflow-view-node",
    "mvc/workflow/workflow-terminals",
    "mvc/workflow/workflow-view-terminals",
    "mvc/workflow/workflow-connector"
], function(
    sinon,
    testApp,
    Utils,
    App,
    Node,
    NodeView,
    Terminals,
    TerminalsView,
    Connector
){
    "use strict";
    window.show_modal = function(a, b, c) {}
    window.hide_modal = function() {}

    // create body and app
    var create_app = function() {
        // build body
        $('body').append(   '<div id="canvas-viewport">' +
                                '<div id="canvas-container"/>' +
                            '</div>' +
                            '<div id="overview">' +
                                '<canvas id="overview-canvas"/>' +
                                '<div id="overview-viewport"/>' +
                            '</div>');

        // build app
        return new App({
            id      : null,
            urls    : { get_datatypes : Galaxy.root + 'api/datatypes/mapping' },
            workflows : []
        });
    };

    module( "Input terminal model test", {
        setup: function( ) {
            testApp.create();
            this.node = new Node( create_app(), {  } );
            this.input = { extensions: [ "txt" ], multiple: false };
            this.input_terminal = new Terminals.InputTerminal( { input: this.input } );
            this.input_terminal.node = this.node;
        },
        teardown: function() {
            testApp.destroy();
        },
        multiple: function( ) {
            this.input.multiple = true;
            this.input_terminal.update( this.input );
        },
        test_connector: function( ) {
            var outputTerminal = new Terminals.OutputTerminal( { datatypes: [ 'input' ] } );
            var inputTerminal = this.input_terminal;
            var connector = new Connector( outputTerminal, inputTerminal );
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
                other.mapOver = function() { return Terminals.NULL_COLLECTION_TYPE_DESCRIPTION; };
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
        ok( this.test_accept( other ) );
    } );

    test( "can accept subclass datatype", function() {
        var other = { node: {}, datatypes: [ "tabular" ] }; // tabular subclass of input txt
        ok( this.test_accept( other ) ) ;
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

    test( "input type can accept any datatype", function() {
        this.input.extensions = [ "input" ];
        this.input_terminal.update( this.input );
        var other = { node: {}, datatypes: [ "binary" ] };
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
        var other = { node: {}, datatypes: [ "tabular" ], mapOver: function() { return new Terminals.CollectionTypeDescription( "list" ) } };
        var self = this;
        this.multiple();
        ok( self.test_accept( other ) );
    } );

    test( "cannot accept list collection for multiple input if collection already connected", function() {
        var other = { node: {}, datatypes: [ "tabular" ], mapOver: function() { return new Terminals.CollectionTypeDescription( "list" ) } };
        var self = this;
        this.multiple();
        this.with_test_connector( function() {
            ok( ! self.test_accept( other ) );
        } );
    } );

    module( "Connector test", {});

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
        var input = { connect: sinon.spy(), element: $("<div>"), isMappedOver: function() { return false; } };
        var output = { connect: sinon.spy(), element: $("<div>"), isMappedOver: function() { return false; } };
        var connector = new Connector( input, output );
        var n = $('#canvas-container').find('canvas').length;
        connector.redraw();
        // Ensure canvas gets set
        ok( connector.canvas );
        // Ensure it got added to canvas container
        equal (n + 1, $('#canvas-container').find('canvas').length);
    } );

    module( "Input collection terminal model test", {
        setup: function( ) {
            testApp.create();
            this.node = new Node(  create_app(), {  } );
            this.input = { extensions: [ "txt" ], collection_types: ["list"] };
            this.input_terminal = new Terminals.InputCollectionTerminal( { input: this.input } );
            this.input_terminal.node = this.node;
        }
    } );

    test( "Collection output can connect to same collection input type", function() {
        var self = this;
        var inputTerminal = self.input_terminal;
        ok( inputTerminal );
        var outputTerminal = new Terminals.OutputCollectionTerminal( {
            datatypes: 'txt',
            collection_type: 'list'
        } );
        outputTerminal.node = {};
        ok( inputTerminal.canAccept( outputTerminal ), "Input terminal " + inputTerminal + " can not accept " + outputTerminal );
    } );

    test( "Collection output cannot connect to different collection input type", function() {
        var self = this;
        var inputTerminal = self.input_terminal;
        var outputTerminal = new Terminals.OutputCollectionTerminal( {
            datatypes: 'txt',
            collection_type: 'paired'
        } );
        outputTerminal.node = {};
        ok( ! inputTerminal.canAccept( outputTerminal ) );
    } );

    module( "Node unit test", {
        setup: function() {
            testApp.create();
            this.input_terminal = { destroy: sinon.spy(), redraw: sinon.spy() };
            this.output_terminal = { destroy: sinon.spy(), redraw: sinon.spy() };
            this.app = create_app();
            this.element = this.app.$newNodeElement( "tool", "newnode" );
            this.node = new Node( this.app, { element: this.element } );
            this.node.input_terminals.i1 = this.input_terminal;
            this.node.output_terminals.o1 = this.output_terminal;
        },
        $: function( selector ) {
            return $( this.node.element.find( selector ) );
        },
        expect_workflow_node_changed: function( f ) {
            var node = this.node;
            var node_changed_spy = sinon.spy( this.app.workflow, "node_changed" );
            f();
            ok( node_changed_spy.calledWith( node ) );
        },
        init_field_data_simple: function(option_overrides) {
            var data = Utils.merge(option_overrides, {
                data_inputs: [ {name: "input1", extensions: [ "data" ] } ],
                data_outputs: [ {name: "output1", extensions: [ "data" ] } ],
                label: null,
            });
            this.node.init_field_data( data );
        },
        update_field_data_with_new_input: function(option_overrides) {
            var new_data = Utils.merge(option_overrides, {
                data_inputs: [
                    { name: "input1", extensions: [ "data" ] },
                    { name: "extra_0|input1", extensions: [ "data" ] },
                ],
                data_outputs: [ {name: "output1", extensions: [ "data" ] } ],
                post_job_actions: "{}",
                label: "New Label"
            });
            this.node.update_field_data( new_data );
        }
    } );

    test( "make active", function() {
        ok( ! this.element.hasClass( "toolForm-active" ) );
        this.node.make_active();
        ok( this.element.hasClass( "toolForm-active" ) );
    } );

    test( "destroy", function() {
        var remove_node_spy = sinon.spy( this.app.workflow, "remove_node" );
        this.node.destroy();
        ok( this.input_terminal.destroy.called );
        ok( this.output_terminal.destroy.called );
        ok( remove_node_spy.calledWith( this.node ) );
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
                workflow_outputs: [ {"output_name": "out1"} ],
                label: "Cat that data.",
            };
            node.init_field_data( data );
            equal( node.type, "tool" );
            equal( node.name, "cat1" );
            equal( node.form_html, "<form>" );
            equal( node.tool_state, "ok" );
            equal( node.tooltip, "tool tooltip" );
            equal( node.annotation, "tool annotation" );
            equal( node.label, "Cat that data." );
            deepEqual( node.post_job_actions, {} );
            deepEqual( node.workflow_outputs, [  {"output_name": "out1"} ] );
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
            equal( test.$( ".nodeTitle" ).text(), "newnode" );
            ok( test.$( ".toolFormTitle" ).find("i").hasClass("fa-wrench") );
        } );
    } );

    test( "node title behavior", function() {
        var test = this;
        this.expect_workflow_node_changed( function( ) {
            // Node created with name newnode
            equal( test.$( ".nodeTitle" ).text(), "newnode" );
            // init_field_data_simple doesn't change label, so it should
            // remain original name.
            test.init_field_data_simple();
            equal( test.$( ".nodeTitle" ).text(), "newnode" );
            // Despite awkward name, update does change the label...
            test.update_field_data_with_new_input();
            equal( test.$( ".nodeTitle" ).text(), "New Label" );
        });
    });

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

    module( "create_node", {
        setup: function() {
            this.app = create_app();
        }
    });

    test( "node added to workflow", function() {
        var add_node_spy = sinon.spy( this.app.workflow, "add_node" );
        var node = this.app.workflow.create_node( "tool", "Cat Files", "cat1" );
        ok( add_node_spy.calledWith( node ) );
    } );

    // global NodeView
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

            var outputTerminal = new Terminals.OutputTerminal( { name: "TestOuptut", datatypes: [ outputType ] } );
            outputTerminal.node = { markChanged: function() {}, post_job_actions: [], hasMappedOverInputTerminals: function() { return false; }, hasConnectedOutputTerminals: function() { return true; } };
            outputTerminal.terminalMapping = { disableMapOver: function() {}, mapOver: Terminals.NULL_COLLECTION_TYPE_DESCRIPTION };
            var c = new Connector( outputTerminal, terminal );

            return c;
        },
        connectAttachedMultiInputTerminal: function( inputType, outputType ) {
            this.view.addDataInput( { name: "TestName", extensions: [ inputType ], multiple: true } );
            var terminal = this.view.node.input_terminals[ "TestName" ];

            var outputTerminal = new Terminals.OutputTerminal( { name: "TestOuptut", datatypes: [ "txt" ] } );
            outputTerminal.node = { markChanged: function() {}, post_job_actions: [], hasMappedOverInputTerminals: function() { return false; }, hasConnectedOutputTerminals: function() { return true; } };
            outputTerminal.terminalMapping = { disableMapOver: function() {}, mapOver: new Terminals.CollectionTypeDescription( "list" ) };
            var c = new Connector( outputTerminal, terminal );

            return c;
        },
        connectAttachedMappedOutput: function( ) {
            this.view.addDataInput( { name: "TestName", extensions: [ "txt" ], input_type: "dataset_collection" } );
            var terminal = this.view.node.input_terminals[ "TestName" ];

            var outputTerminal = new Terminals.OutputTerminal( { name: "TestOuptut", datatypes: [ "txt" ] } );
            outputTerminal.node = { markChanged: function() {}, post_job_actions: [], hasMappedOverInputTerminals: function() { return false; }, hasConnectedOutputTerminals: function() { return true; } };
            outputTerminal.terminalMapping = { disableMapOver: function() {}, mapOver: new Terminals.CollectionTypeDescription( "list" ) };
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

    // global InputTerminalView
    module( "Input terminal view", {
        setup: function() {
            this.node = { input_terminals: [] };
            this.input = { name: "i1", extensions: "txt", multiple: false };
            this.view = new TerminalsView.InputTerminalView( {
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

    // global OutputTerminalView
    module( "Output terminal view", {
        setup: function() {
            this.node = { output_terminals: [] };
            this.output = { name: "o1", extensions: "txt" };
            this.view = new TerminalsView.OutputTerminalView( {
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

    module( "CollectionTypeDescription", {
        listType: function() {
            return new Terminals.CollectionTypeDescription( "list" );
        },
        pairedType: function() {
            return new Terminals.CollectionTypeDescription( "paired" );
        },
        pairedListType: function() {
            return new Terminals.CollectionTypeDescription( "list:paired" );
        }
    } );

    test( "canMatch", function() {
        ok( this.listType().canMatch( this.listType() ) );
        ok( ! this.listType().canMatch( this.pairedType() ) );
        ok( ! this.listType().canMatch( this.pairedListType() ) );
    } );

    test( "canMatch special types", function() {
        ok( this.listType().canMatch( Terminals.ANY_COLLECTION_TYPE_DESCRIPTION ) );
        ok( Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.canMatch( this.pairedListType() ) );

        ok( ! this.listType().canMatch( Terminals.NULL_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.canMatch( this.pairedListType() ) );
    } );

    test( "canMapOver", function() {
        ok( ! this.listType().canMapOver( this.listType() ) );
        ok( ! this.listType().canMapOver( this.pairedType() ) );
        ok( this.pairedListType().canMapOver( this.pairedType() ) );
        ok( ! this.listType().canMapOver( this.pairedListType() ) );
    } );

    test( "canMapOver special types", function() {
        ok( ! this.listType().canMapOver( Terminals.NULL_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.canMapOver( this.pairedListType() ) );

        // Following two should be able to be relaxed someday maybe - but the
        // tracking gets tricky I think. For now mapping only works for explicitly
        // defined collection types.
        ok( ! this.listType().canMapOver( Terminals.ANY_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.canMapOver( this.pairedListType() ) );
    } );

    test( "append", function( other ) {
        var appendedType = this.listType().append( this.pairedType() );
        equal( appendedType.collectionType, "list:paired" );
    } );

    test( "isCollection", function() {
        ok( this.listType().isCollection );
        ok( Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.isCollection );
        ok( ! Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.isCollection );
    } );

    test( "equal", function() {
        ok( ! this.listType().equal( this.pairedType() ) );
        ok( this.listType().equal( this.listType() ) );

        ok( Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.equal( Terminals.ANY_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.equal( Terminals.NULL_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.equal( this.pairedType() ) );
        ok( ! this.pairedType().equal( Terminals.ANY_COLLECTION_TYPE_DESCRIPTION ) );

        ok( Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.equal( Terminals.NULL_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.equal( Terminals.ANY_COLLECTION_TYPE_DESCRIPTION ) );
        ok( ! Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.equal( this.listType() ) );
        ok( ! this.listType().equal( Terminals.NULL_COLLECTION_TYPE_DESCRIPTION ) );

    } );

    module( "TerminalMapping", {
    } );

    test( "default constructor", function() {
        var terminal = {};
        var mapping = new Terminals.TerminalMapping( { terminal: terminal } );
        ok( terminal.terminalMapping === mapping );
        ok( mapping.mapOver === Terminals.NULL_COLLECTION_TYPE_DESCRIPTION );
    } );

    test( "constructing with mapOver", function() {
        var terminal = {};
        var mapping = new Terminals.TerminalMapping( { terminal: terminal, mapOver: new Terminals.CollectionTypeDescription( "list" ) } );
        ok( mapping.mapOver.collectionType == "list" );
    } );

    test( "disableMapOver", function() {
        var terminal = {};
        var mapping = new Terminals.TerminalMapping( { terminal: terminal, mapOver: new Terminals.CollectionTypeDescription( "list" ) } );
        var changeSpy = sinon.spy();
        mapping.bind( "change", changeSpy );
        mapping.disableMapOver();
        ok( mapping.mapOver === Terminals.NULL_COLLECTION_TYPE_DESCRIPTION );
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
            var inputTerminal = new Terminals.InputTerminal( { element: inputEl, input: input } );
            var inputTerminalMapping = new Terminals.TerminalMapping( { terminal: inputTerminal } );
            inputTerminal.node = node;
            if( mapOver ) {
                inputTerminal.setMapOver( new Terminals.CollectionTypeDescription( mapOver ) );
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
            var inputTerminal = new Terminals.InputCollectionTerminal( { element: inputEl, input: input } );
            var inputTerminalMapping = new Terminals.TerminalMapping( { terminal: inputTerminal } );
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
            var outputTerminal = new Terminals.OutputTerminal( { element: outputEl, datatypes: output.extensions } );
            var outputTerminalMapping = new Terminals.TerminalMapping( { terminal: outputTerminal } );
            outputTerminal.node = node;
            if( mapOver ) {
                outputTerminal.setMapOver( new Terminals.CollectionTypeDescription( mapOver ) );
            }
            return outputTerminal;
        },
        newOutputCollectionTerminal: function( collectionType, output, node, mapOver ) {
            collectionType = collectionType || "list";
            output = output || {};
            node = node || this.newNode();
            if( ! ( 'extensions' in output ) ) {
                output[ 'extensions'] = [ 'data' ];
            }
            var outputEl = $("<div>")[ 0 ];
            var outputTerminal = new Terminals.OutputCollectionTerminal( { element: outputEl, datatypes: output.extensions, collection_type: collectionType } );
            var outputTerminalMapping = new Terminals.TerminalMapping( { terminal: outputTerminal } );
            outputTerminal.node = node;
            if( mapOver ) {
                outputTerminal.setMapOver( new Terminals.CollectionTypeDescription( mapOver ) );
            }
            return outputTerminal;
        },
        newNode: function( ) {
            var nodeEl = $("<div>")[ 0 ];
            var node = new Node( create_app(), { element: nodeEl } );
            return node;
        },
        _addExistingOutput: function( terminal, output, connected ) {
            var self = this;
            var node = terminal.node;
            if( connected ) {
                var inputTerminal = self.newInputTerminal();
                new Connector( inputTerminal, output );
            }
            this._addTerminalTo( output, node.output_terminals );
            return output;
        },
        addOutput: function( terminal, connected ) {
            var connectedOutput = this.newOutputTerminal();
            return this._addExistingOutput( terminal, connectedOutput, connected );
        },
        addCollectionOutput: function( terminal, connected ) {
            var collectionOutput = this.newOutputCollectionTerminal();
            return this._addExistingOutput( terminal, collectionOutput, connected );
        },
        addConnectedOutput: function( terminal ) {
            return this.addOutput( terminal, true );
        },
        addConnectedCollectionOutput: function( terminal ) {
            var connectedOutput = this.newOutputCollectionTerminal();
            return this._addExistingOutput( terminal, connectedOutput, true );
        },
        addConnectedInput: function( terminal ) {
            var self = this;
            var connectedInput = this.newInputTerminal();
            var node = terminal.node;
            var outputTerminal = self.newOutputTerminal();
            new Connector( connectedInput, outputTerminal );
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

            ok( inputTerminal.attachable( outputTerminal ), 'Cannot attach '+ outputTerminal + " to " + inputTerminal );

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
        connectedInput2.setMapOver( new Terminals.CollectionTypeDescription( "list") );
        this.verifyAttachable( inputTerminal1, "list" );
    } );

    test( "unmapped input cannot be mapped over if not matching connected input terminals map type", function() {
        var inputTerminal1 = this.newInputTerminal();
        var connectedInput = this.addConnectedInput( inputTerminal1 );
        connectedInput.setMapOver( new Terminals.CollectionTypeDescription( "paired" ) );
        this.verifyNotAttachable( inputTerminal1, "list" );
    } );

    test( "unmapped input can be attached to by output collection if matching connected input terminals map type", function() {
        var inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput( inputTerminal1 );
        var connectedInput2 = this.addConnectedInput( inputTerminal1 );
        connectedInput2.setMapOver( new Terminals.CollectionTypeDescription( "list") );
        var outputTerminal = this.newOutputCollectionTerminal( "list" );
        this.verifyAttachable( inputTerminal1, outputTerminal );
    } );

    test( "unmapped input cannot be attached to by output collection if matching connected input terminals don't match map type", function() {
        var inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput( inputTerminal1 );
        var connectedInput2 = this.addConnectedInput( inputTerminal1 );
        connectedInput2.setMapOver( new Terminals.CollectionTypeDescription( "list") );
        var outputTerminal = this.newOutputCollectionTerminal( "paired" );
        this.verifyNotAttachable( inputTerminal1, outputTerminal );
    } );

    test( "unmapped input can be attached to by output collection if effective output type (output+mapover) is same as mapped over input", function() {
        var inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput( inputTerminal1 );
        var connectedInput2 = this.addConnectedInput( inputTerminal1 );
        connectedInput2.setMapOver( new Terminals.CollectionTypeDescription( "list:paired") );
        var outputTerminal = this.newOutputCollectionTerminal( "paired" );
        outputTerminal.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        this.verifyAttachable( inputTerminal1, outputTerminal );
    } );

    test( "unmapped input cannot be attached to by output collection if effective output type (output+mapover) is not same as mapped over input (1)", function() {
        var inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput( inputTerminal1 );
        var connectedInput2 = this.addConnectedInput( inputTerminal1 );
        connectedInput2.setMapOver( new Terminals.CollectionTypeDescription( "list:paired") );
        var outputTerminal = this.newOutputCollectionTerminal( "list" );
        outputTerminal.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        this.verifyNotAttachable( inputTerminal1, outputTerminal );
    } );

    test( "unmapped input cannot be attached to by output collection if effective output type (output+mapover) is not same as mapped over input (2)", function() {
        var inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput( inputTerminal1 );
        var connectedInput2 = this.addConnectedInput( inputTerminal1 );
        connectedInput2.setMapOver( new Terminals.CollectionTypeDescription( "list:paired") );
        var outputTerminal = this.newOutputCollectionTerminal( "list" );
        outputTerminal.setMapOver( new Terminals.CollectionTypeDescription( "paired" ) );
        this.verifyNotAttachable( inputTerminal1, outputTerminal );
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
        connectedOutput.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        this.verifyAttachable( inputTerminal1, "list" );
    } );

    test( "unmapped input with connected mapped outputs cannot be mapped over if mapover not matching", function() {
        // It would invalidate the connections - someday maybe we could try to
        // recursively map over everything down the DAG - it would be expensive
        // to check that though.
        var inputTerminal1 = this.newInputTerminal();
        var connectedOutput = this.addConnectedOutput( inputTerminal1 );
        connectedOutput.setMapOver( new Terminals.CollectionTypeDescription( "paired" ) );
        this.verifyNotAttachable( inputTerminal1, "list" );
    } );

    test( "explicitly constrained input can not be mapped over by incompatible collection type", function() {
        var inputTerminal1 = this.newInputTerminal();
        inputTerminal1.setMapOver( new Terminals.CollectionTypeDescription( "paired" ) );
        this.verifyNotAttachable( inputTerminal1, "list" );
    } );

    test( "explicitly constrained input can be mapped over by compatible collection type", function() {
        var inputTerminal1 = this.newInputTerminal();
        inputTerminal1.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        this.verifyAttachable( inputTerminal1, "list" );
    } );

    test( "unconstrained collection input can be mapped over", function() {
        var inputTerminal1 = this.newInputCollectionTerminal( { collection_types: ["paired"] } );
        this.verifyAttachable( inputTerminal1, "list:paired" );
    } );

    test( "unconstrained collection input cannot be mapped over by incompatible type", function() {
        var inputTerminal1 = this.newInputCollectionTerminal( { collection_types: ["list"] } ); // Would need to be paired...
        this.verifyNotAttachable( inputTerminal1, "list:paired" );
    } );

    test( "explicitly mapped over collection input can be attached by explicit mapping", function() {
        var inputTerminal1 = this.newInputCollectionTerminal( { collection_types: ["paired"] } );
        inputTerminal1.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        this.verifyAttachable( inputTerminal1, "list:paired" );
    } );

    test( "explicitly mapped over collection input can be attached by explicit mapping", function() {
        var inputTerminal1 = this.newInputCollectionTerminal( { collection_types: ["list:paired"] } );
        inputTerminal1.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
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
        connectedOutput.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        inputTerminal1.resetMappingIfNeeded();
        this.verifyMappedOver( inputTerminal1 );
    } );

    test( "resetMappingIfNeeded resets if node outputs are not connected to anything", function() {
        var inputTerminal1 = this.newInputTerminal( "list" );
        var output = this.addOutput( inputTerminal1 );
        output.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        inputTerminal1.resetMappingIfNeeded();
        this.verifyNotMappedOver( inputTerminal1 );
    } );

    test( "resetMappingIfNeeded an input resets node outputs if they not connected to anything", function() {
        var inputTerminal1 = this.newInputTerminal( "list" );
        var output = this.addOutput( inputTerminal1 );
        output.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        inputTerminal1.resetMappingIfNeeded();
        this.verifyNotMappedOver( output );
    } );

    test( "resetMappingIfNeeded an input resets node collection outputs if they not connected to anything", function() {
        var inputTerminal1 = this.newInputTerminal( "list" );
        var output = this.addCollectionOutput( inputTerminal1 );
        output.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        inputTerminal1.resetMappingIfNeeded();
        this.verifyNotMappedOver( output );
    } );

    test( "resetMappingIfNeeded resets if not last mapped over input", function() {
        // Idea here is that other nodes are forcing output to still be mapped
        // over so don't need to disconnect output nodes.
        var inputTerminal1 = this.newInputTerminal( "list" );
        var connectedInput1 = this.addConnectedInput( inputTerminal1 );
        connectedInput1.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        var connectedOutput = this.addConnectedOutput( inputTerminal1 );
        connectedOutput.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );
        inputTerminal1.resetMappingIfNeeded();
        // inputTerminal1 can be reset because connectedInput1
        // is still forcing connectedOutput to be mapped over,
        // so verify inputTerminal1 is rest and connectedInput1
        // and connectedOutput are untouched.
        this.verifyNotMappedOver( inputTerminal1 );
        this.verifyMappedOver( connectedInput1 );
        this.verifyMappedOver( connectedOutput );
    } );

    test( "simple mapping over collection outputs works correctly", function() {
        var inputTerminal1 = this.newInputTerminal();
        var connectedOutput = this.addConnectedCollectionOutput( inputTerminal1 );
        inputTerminal1.setMapOver( new Terminals.CollectionTypeDescription( "list" ) );

        // Can attach list output of collection type list that is being mapped
        // over another list to a list:list (because this is what it is) but not
        // to a list:list:list.
        var testTerminal2 = this.newInputTerminal( "list:list" );
        this.verifyAttachable( testTerminal2, connectedOutput );

        var testTerminal1 = this.newInputTerminal( "list:list:list" );
        this.verifyNotAttachable( testTerminal1, connectedOutput );
    } );
});