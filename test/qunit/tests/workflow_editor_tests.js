/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
/* global Workflow, CanvasManager, InputTerminal, Connector, add_node */
define([
    "galaxy.workflow_editor.canvas",
    "jquery",
    "sinon-qunit"
], function(
    workflowEditor,
    $,
    sinon
){
    "use strict";

    // globals cosumed by workflow editor
    window.show_form_for_tool = sinon.spy();
    window.workflow = null;
    window.canvas_manager = null;

    // Stub used over stubbing issubtype for unit testing datatype comparisons.
    var issubtypeStub = null;

    QUnit.moduleStart(function() {
        if( issubtypeStub === null) {
            issubtypeStub = sinon.stub( window, "issubtype" );
        }
    });
    QUnit.moduleDone(function() {
        if( issubtypeStub !== null) {
            issubtypeStub.restore();
            issubtypeStub = null;
        }
    });

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
        setup: function() {
            this.node = {  };
            this.element = $( "<div>" );
            this.input_terminal = new InputTerminal( this.element, [ "txt" ] );
            this.input_terminal.node = this.node;
        },
        test_connector: function( attr ) {
            var connector = attr || {};
            this.input_terminal.connectors.push( connector );
            return connector;
        },
        with_test_connector: function( attr, f ) {
            this.test_connector( attr );
            f();
            this.reset_connectors();
        },
        reset_connectors: function( ) {
            this.input_terminal.connectors = [];
        },
        test_accept: function( other ) {
            other = other || { node: {}, datatypes: [ "txt" ] };
            return this.input_terminal.can_accept( other );
        }
    } );

    test( "test connect", function() {
        this.node.changed = sinon.spy();

        var connector = {};
        this.input_terminal.connect( connector );

        // Assert node changed called
        ok( this.node.changed.called );
        // Assert connectors updated
        ok( this.input_terminal.connectors[ 0 ] === connector );
    } );

    test( "test disconnect", function() {
        this.node.changed = sinon.spy();

        var connector = this.test_connector( {} );
        this.input_terminal.disconnect( connector );

        // Assert node changed called
        ok( this.node.changed.called );
        // Assert connectors updated
        equal( this.input_terminal.connectors.length, 0 );
    } );

    test( "test redraw", function() {
        var connector = this.test_connector( { redraw: sinon.spy() } );
        this.input_terminal.redraw();
        // Assert connectors were redrawn
        ok( connector.redraw.called );
    } );

    test( "test destroy", function() {
        var connector = this.test_connector( { destroy: sinon.spy() } );

        this.input_terminal.destroy();
        // Assert connectors were redrawn
        ok( connector.destroy.called );
    } );

    test( "can accept correct datatype", function() {
        issubtypeStub.returns(true);
        ok( this.test_accept() ) ;
    } );

    test( "cannot accept incorrect datatypes", function() {
        issubtypeStub.returns(false);
        ok( ! this.test_accept() );
    } );

    test( "can accept inputs", function() {
        issubtypeStub.returns(false);
        // Other is data input module - always accept (currently - could be
        // more intelligent by looking at what else input is connected to.
        var other = { node: {}, datatypes: [ "input" ] };
        ok( this.test_accept( other ) );
    } );

    test( "cannot accept when already connected", function() {
        issubtypeStub.returns(true);
        var self = this;
        // If other is subtype but already connected, cannot accept
        this.with_test_connector( {}, function() {
            ok( ! self.test_accept() );
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
            var input = { connect: sinon.spy(), element: $("<div>") };
            var output = { connect: sinon.spy(), element: $("<div>") };
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
            this.node = new Node( this.element );
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

            test.update_field_data_with_new_input();
            
            var new_input_terminal = node.input_terminals.input1;
            equal( old_input_terminal, old_input_terminal );
            notEqual( old_input_terminal, new_input_terminal );
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
            this.set_for_node( {} );
        },
        set_for_node: function( node ) {
            var element = $("<div>");
            this.view = new NodeView( { node: node, el: element[ 0 ] } );
        },
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

});