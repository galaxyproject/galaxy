/* global QUnit */
import $ from "jquery";
import testApp from "qunit/test-app";
import sinon from "sinon";
import Utils from "utils/utils";
import App from "mvc/workflow/workflow-view";
import Node from "mvc/workflow/workflow-node";
import NodeView from "mvc/workflow/workflow-view-node";
import Terminals from "mvc/workflow/workflow-terminals";
import TerminalsView from "mvc/workflow/workflow-view-terminals";
import Connector from "mvc/workflow/workflow-connector";
import { getAppRoot } from "onload/loadConfig";

// window.show_modal = function(a, b, c) {};
// window.hide_modal = function() {};

// create body and app
var create_app = function() {
    // build body
    $("body").append(
        '<div id="canvas-viewport">' +
            '<div id="canvas-container"/>' +
            "</div>" +
            '<div id="overview">' +
            '<canvas id="overview-canvas"/>' +
            '<div id="overview-viewport"/>' +
            "</div>"
    );

    // build app
    return new App({
        id: null,
        urls: { get_datatypes: getAppRoot() + "api/datatypes/mapping" },
        workflows: []
    });
};

QUnit.module("Input terminal model test", {
    beforeEach: function() {
        testApp.create();
        this.node = new Node(create_app(), {});
        this.input = { extensions: ["txt"], multiple: false };
        this.input_terminal = new Terminals.InputTerminal({ input: this.input });
        this.input_terminal.node = this.node;
    },
    afterEach: function() {
        testApp.destroy();
        delete this.node;
    },
    multiple: function() {
        this.input.multiple = true;
        this.input_terminal.update(this.input);
    },
    test_connector: function() {
        var outputTerminal = new Terminals.OutputTerminal({ datatypes: ["input"] });
        var inputTerminal = this.input_terminal;
        var connector = new Connector(outputTerminal, inputTerminal);
        return connector;
    },
    with_test_connector: function(f) {
        this.test_connector();
        f();
        this.reset_connectors();
    },
    reset_connectors: function() {
        this.input_terminal.connectors = [];
    },
    test_accept: function(other) {
        other = other || { node: {}, datatypes: ["txt"] };
        if (!other.mapOver) {
            other.mapOver = function() {
                return Terminals.NULL_COLLECTION_TYPE_DESCRIPTION;
            };
        }
        return this.input_terminal.canAccept(other);
    },
    pja_change_datatype_node: function(output_name, newtype) {
        var pja = {
            action_type: "ChangeDatatypeAction",
            output_name: output_name,
            action_arguments: { newtype: newtype }
        };
        var otherNode = { post_job_actions: [pja] };
        return otherNode;
    }
});

QUnit.test("test update", function(assert) {
    assert.deepEqual(this.input_terminal.datatypes, ["txt"]);
    assert.equal(this.input_terminal.multiple, false);
    this.input_terminal.update({ extensions: ["bam"], multiple: true });
    assert.deepEqual(this.input_terminal.datatypes, ["bam"]);
    assert.equal(this.input_terminal.multiple, true);
});

QUnit.test("test connect", function(assert) {
    this.node.markChanged = sinon.spy();
    var connector = {};
    this.input_terminal.connect(connector);
    // Assert node markChanged called
    assert.ok(this.node.markChanged.called);
    // Assert connectors updated
    assert.ok(this.input_terminal.connectors[0] === connector);
});

QUnit.test("test disconnect", function(assert) {
    this.node.markChanged = sinon.spy();
    var connector = this.test_connector();
    this.input_terminal.disconnect(connector);
    // Assert node markChanged called
    assert.ok(this.node.markChanged.called);
    // Assert connectors updated
    assert.equal(this.input_terminal.connectors.length, 0);
});

QUnit.test("test redraw", function(assert) {
    var connector = this.test_connector();
    connector.redraw = sinon.spy();
    this.input_terminal.redraw();
    // Assert connectors were redrawn
    assert.ok(connector.redraw.called);
});

QUnit.test("test destroy", function(assert) {
    var connector = this.test_connector();
    connector.destroy = sinon.spy();
    this.input_terminal.destroy();
    // Assert connectors were destroyed
    assert.ok(connector.destroy.called);
});

QUnit.test("can accept exact datatype", function(assert) {
    var other = { node: {}, datatypes: ["txt"] }; // input also txt
    assert.ok(this.test_accept(other));
});

QUnit.test("can accept subclass datatype", function(assert) {
    var other = { node: {}, datatypes: ["tabular"] }; // tabular subclass of input txt
    assert.ok(this.test_accept(other));
});

QUnit.test("cannot accept incorrect datatype", function(assert) {
    var other = { node: {}, datatypes: ["binary"] }; // binary is not txt
    assert.ok(!this.test_accept(other));
});

QUnit.test("can accept incorrect datatype if converted with PJA", function(assert) {
    var otherNode = this.pja_change_datatype_node("out1", "txt");
    var other = { node: otherNode, datatypes: ["binary"], name: "out1" }; // Was binary but converted to txt
    assert.ok(this.test_accept(other));
});

QUnit.test("cannot accept incorrect datatype if converted with PJA to incompatible type", function(assert) {
    var otherNode = this.pja_change_datatype_node("out1", "bam"); // bam's are not txt
    var other = { node: otherNode, datatypes: ["binary"], name: "out1" };
    assert.ok(!this.test_accept(other));
});

QUnit.test("cannot accept incorrect datatype if some other output converted with PJA to compatible type", function(
    assert
) {
    var otherNode = this.pja_change_datatype_node("out2", "txt");
    var other = { node: otherNode, datatypes: ["binary"], name: "out1" };
    assert.ok(!this.test_accept(other));
});

QUnit.test("can accept inputs", function(assert) {
    // Other is data input module - always accept (currently - could be
    // more intelligent by looking at what else input is connected to.
    var other = { node: {}, datatypes: ["input"] };
    assert.ok(this.test_accept(other));
});

QUnit.test("input type can accept any datatype", function(assert) {
    this.input.extensions = ["input"];
    this.input_terminal.update(this.input);
    var other = { node: {}, datatypes: ["binary"] };
    assert.ok(this.test_accept(other));
});

QUnit.test("cannot accept when already connected", function(assert) {
    var self = this;
    // If other is subtype but already connected, cannot accept
    this.with_test_connector(function() {
        assert.ok(!self.test_accept());
    });
});

QUnit.test("can accept already connected inputs if input is multiple", function(assert) {
    var self = this;
    this.multiple();
    this.with_test_connector(function() {
        assert.ok(self.test_accept());
    });
});

QUnit.test("cannot accept already connected inputs if input is multiple but datatypes don't match", function(assert) {
    var other = { node: {}, datatypes: ["binary"] }; // binary is not txt

    var self = this;
    this.multiple();
    this.with_test_connector(function() {
        assert.ok(!self.test_accept(other));
    });
});

QUnit.test("can accept list collection for multiple input parameters if datatypes match", function(assert) {
    var self = this;
    this.multiple();
    assert.ok(self.test_accept());
});

QUnit.test("can accept list collection for empty multiple inputs", function(assert) {
    var other = {
        node: {},
        datatypes: ["tabular"],
        mapOver: function() {
            return new Terminals.CollectionTypeDescription("list");
        }
    };
    var self = this;
    this.multiple();
    assert.ok(self.test_accept(other));
});

QUnit.test("cannot accept list collection for multiple input if collection already connected", function(assert) {
    var other = {
        node: {},
        datatypes: ["tabular"],
        mapOver: function() {
            return new Terminals.CollectionTypeDescription("list");
        }
    };
    var self = this;
    this.multiple();
    this.with_test_connector(function() {
        assert.ok(!self.test_accept(other));
    });
});

QUnit.module("Connector test", {});

QUnit.test("connects only if both valid handles", function(assert) {
    var input = { connect: sinon.spy() };
    var output = { connect: sinon.spy() };
    new Connector(input, null);
    new Connector(null, output);
    // Not attempts to connect...
    assert.ok(!input.connect.called);
    assert.ok(!output.connect.called);
    new Connector(input, output);
    assert.ok(input.connect.called);
    assert.ok(output.connect.called);
});

QUnit.test("default attributes", function(assert) {
    var input = { connect: sinon.spy() };
    var output = { connect: sinon.spy() };
    var connector = new Connector(input, output);
    assert.equal(connector.dragging, false);
    assert.equal(connector.canvas, null);
    assert.equal(connector.inner_color, "#FFFFFF");
    assert.equal(connector.outer_color, "#25537b");
});

QUnit.test("destroy", function(assert) {
    var input = { connect: sinon.spy(), disconnect: sinon.spy() };
    var output = { connect: sinon.spy(), disconnect: sinon.spy() };
    var connector = new Connector(input, output);
    connector.destroy();
    assert.ok(input.disconnect.called);
    assert.ok(output.disconnect.called);
});

QUnit.test("initial redraw", function(assert) {
    var input = {
        connect: sinon.spy(),
        element: $("<div>"),
        isMappedOver: function() {
            return false;
        }
    };
    var output = {
        connect: sinon.spy(),
        element: $("<div>"),
        isMappedOver: function() {
            return false;
        }
    };
    var connector = new Connector(input, output);
    var n = $("#canvas-container").find("canvas").length;
    connector.redraw();
    // Ensure canvas gets set
    assert.ok(connector.canvas);
    // Ensure it got added to canvas container
    assert.equal(n + 1, $("#canvas-container").find("canvas").length);
});

QUnit.module("Input collection terminal model test", {
    beforeEach: function() {
        testApp.create();
        this.node = new Node(create_app(), {});
        this.input = { extensions: ["txt"], collection_types: ["list"] };
        this.input_terminal = new Terminals.InputCollectionTerminal({ input: this.input });
        this.input_terminal.node = this.node;
    },
    afterEach: function() {
        testApp.destroy();
    }
});

QUnit.test("Collection output can connect to same collection input type", function(assert) {
    var self = this;
    var inputTerminal = self.input_terminal;
    assert.ok(inputTerminal);
    var outputTerminal = new Terminals.OutputCollectionTerminal({
        datatypes: "txt",
        collection_type: "list"
    });
    outputTerminal.node = {};
    assert.ok(
        inputTerminal.canAccept(outputTerminal),
        "Input terminal " + inputTerminal + " can not accept " + outputTerminal
    );
});

QUnit.test("Collection output cannot connect to different collection input type", function(assert) {
    var self = this;
    var inputTerminal = self.input_terminal;
    var outputTerminal = new Terminals.OutputCollectionTerminal({
        datatypes: "txt",
        collection_type: "paired"
    });
    outputTerminal.node = {};
    assert.ok(!inputTerminal.canAccept(outputTerminal));
});

QUnit.module("Node unit test", {
    beforeEach: function() {
        testApp.create();
        this.input_terminal = { destroy: sinon.spy(), redraw: sinon.spy() };
        this.output_terminal = { destroy: sinon.spy(), redraw: sinon.spy() };
        this.app = create_app();
        this.node = this.app.prebuildNode("tool", "newnode");
        this.element = this.node.element;
        this.node.input_terminals.i1 = this.input_terminal;
        this.node.output_terminals.o1 = this.output_terminal;
    },
    afterEach: function() {
        testApp.destroy();
    },
    $: function(selector) {
        return $(this.node.element.find(selector));
    },
    expect_workflow_node_changed: function(assert, f) {
        var node = this.node;
        var node_changed_spy = sinon.spy(this.app.workflow, "node_changed");
        f();
        assert.ok(node_changed_spy.calledWith(node));
    },
    init_field_data_simple: function(option_overrides) {
        var data = Utils.merge(option_overrides, {
            inputs: [{ name: "input1", extensions: ["data"] }],
            outputs: [{ name: "output1", extensions: ["data"] }],
            label: null
        });
        this.node.init_field_data(data);
    },
    update_field_data_with_new_input: function(option_overrides) {
        var new_data = Utils.merge(option_overrides, {
            inputs: [{ name: "input1", extensions: ["data"] }, { name: "extra_0|input1", extensions: ["data"] }],
            outputs: [{ name: "output1", extensions: ["data"] }],
            post_job_actions: "{}",
            label: "New Label"
        });
        this.node.update_field_data(new_data);
    }
});

QUnit.test("make active", function(assert) {
    assert.ok(!this.element.hasClass("toolForm-active"));
    this.node.make_active();
    assert.ok(this.element.hasClass("toolForm-active"));
});

QUnit.test("destroy", function(assert) {
    var remove_node_spy = sinon.spy(this.app.workflow, "remove_node");
    this.node.destroy();
    assert.ok(this.input_terminal.destroy.called);
    assert.ok(this.output_terminal.destroy.called);
    assert.ok(remove_node_spy.calledWith(this.node));
});

QUnit.test("error", function(assert) {
    // Test body of toolFormBody div updated and workflow notified of change.
    var test = this;
    this.expect_workflow_node_changed(assert, function() {
        test.node.error("TOOL ERROR");
        assert.equal($(test.$(".toolFormBody").children()[0]).html(), "TOOL ERROR");
    });
});

QUnit.test("init_field_data properties", function(assert) {
    var node = this.node;
    this.expect_workflow_node_changed(assert, function() {
        var data = {
            inputs: [],
            outputs: [],
            type: "tool",
            name: "cat1",
            config_form: "{}",
            tool_state: "ok",
            tool_errors: false,
            tooltip: "tool tooltip",
            annotation: "tool annotation",
            workflow_outputs: [{ output_name: "out1" }],
            label: "Cat that data."
        };
        node.init_field_data(data);
        assert.equal(node.type, "tool");
        assert.equal(node.name, "cat1");
        assert.equal(node.config_form, "{}");
        assert.equal(node.tool_state, "ok");
        assert.equal(node.tooltip, "tool tooltip");
        assert.equal(node.annotation, "tool annotation");
        assert.equal(node.label, "Cat that data.");
        assert.deepEqual(node.post_job_actions, {});
        assert.deepEqual(node.workflow_outputs, [{ output_name: "out1" }]);
    });
});

QUnit.test("init_field_data data", function(assert) {
    var test = this;
    this.expect_workflow_node_changed(assert, function() {
        // pre-init not tool form body...
        assert.equal(test.$(".output-terminal").length, 0);
        assert.equal(test.$(".input-terminal").length, 0);
        assert.equal(test.$(".rule").length, 0);
        test.init_field_data_simple();
        // After init tool form should have three "rows"/divs - , inputs div, one output, and rule...
        assert.equal(test.$(".output-terminal").length, 1);
        assert.equal(test.$(".input-terminal").length, 1);
        assert.equal(test.$(".rule").length, 1);
        assert.equal(test.$(".toolFormBody").children().length, 3);
        assert.equal(test.$(".nodeTitle").text(), "newnode");
        assert.ok(
            test
                .$(".toolFormTitle")
                .find("i")
                .hasClass("fa-wrench")
        );
    });
});

QUnit.test("node title behavior", function(assert) {
    var test = this;
    this.expect_workflow_node_changed(assert, function() {
        // Node created with name newnode
        assert.equal(test.$(".nodeTitle").text(), "newnode");
        // init_field_data_simple doesn't change label, so it should
        // remain original name.
        test.init_field_data_simple();
        assert.equal(test.$(".nodeTitle").text(), "newnode");
        // Despite awkward name, update does change the label...
        test.update_field_data_with_new_input();
        assert.equal(test.$(".nodeTitle").text(), "New Label");
    });
});

QUnit.test("update_field_data updated data inputs and outputs", function(assert) {
    var test = this;
    this.expect_workflow_node_changed(assert, function() {
        // Call init with one input and output.
        test.init_field_data_simple();

        test.update_field_data_with_new_input();

        // Now there are 2 inputs...
        assert.equal(test.$(".input-terminal").length, 2);
        assert.equal(test.$(".output-terminal").length, 1);
        assert.equal(test.$(".rule").length, 1);
    });
});

QUnit.test("update_field_data preserves connectors", function(assert) {
    var test = this;
    var node = this.node;
    this.expect_workflow_node_changed(assert, function() {
        // Call init with one input and output.
        test.init_field_data_simple();

        var connector = new Connector();
        var old_input_terminal = node.input_terminals.input1;
        old_input_terminal.connectors.push(connector);

        // Update node, make sure connector still the same...
        test.update_field_data_with_new_input();
        var new_input_terminal = node.input_terminals.input1;
        assert.equal(connector, new_input_terminal.connectors[0]);

        // Update a second time, make sure connector still the same...
        test.update_field_data_with_new_input();
        new_input_terminal = node.input_terminals.input1;
        assert.equal(connector, new_input_terminal.connectors[0]);
    });
});

QUnit.test("update_field_data destroys old terminals", function(assert) {
    var test = this;
    var node = this.node;
    this.expect_workflow_node_changed(assert, function() {
        var data = {
            inputs: [{ name: "input1", extensions: ["data"] }, { name: "willDisappear", extensions: ["data"] }],
            outputs: [{ name: "output1", extensions: ["data"] }]
        };
        node.init_field_data(data);
        var old_input_terminal = node.input_terminals.willDisappear;
        var destroy_spy = sinon.spy(old_input_terminal, "destroy");
        // Update
        test.update_field_data_with_new_input();
        assert.ok(destroy_spy.called);
    });
});

QUnit.module("create_node", {
    beforeEach: function() {
        testApp.create();
        this.app = create_app();
    },
    afterEach: function() {
        testApp.destroy();
    }
});

QUnit.test("node added to workflow", function(assert) {
    var add_node_spy = sinon.spy(this.app.workflow, "add_node");
    var node = this.app.workflow.create_node("tool", "Cat Files", "cat1");
    assert.ok(add_node_spy.calledWith(node));
});

// global NodeView
QUnit.module("Node view ", {
    beforeEach: function() {
        this.set_for_node({
            input_terminals: {},
            output_terminals: {},
            markChanged: function() {},
            terminalMapping: { disableMapOver: function() {} }
        });
    },
    afterEach: function() {
        this.view.$el.remove();
    },
    set_for_node: function(node) {
        var element = $("<div><div class='toolFormBody'></div></div>");
        this.view = new NodeView({ node: node, el: element[0] });
    },
    connectAttachedTerminal: function(inputType, outputType) {
        this.view.addDataInput({ name: "TestName", extensions: [inputType] });
        var terminal = this.view.node.input_terminals["TestName"];

        var outputTerminal = new Terminals.OutputTerminal({ name: "TestOuptut", datatypes: [outputType] });
        outputTerminal.node = {
            markChanged: function() {},
            post_job_actions: [],
            hasMappedOverInputTerminals: function() {
                return false;
            },
            hasConnectedOutputTerminals: function() {
                return true;
            }
        };
        outputTerminal.terminalMapping = {
            disableMapOver: function() {},
            mapOver: Terminals.NULL_COLLECTION_TYPE_DESCRIPTION
        };
        var c = new Connector(outputTerminal, terminal);

        return c;
    },
    connectAttachedMultiInputTerminal: function(inputType, outputType) {
        this.view.addDataInput({ name: "TestName", extensions: [inputType], multiple: true });
        var terminal = this.view.node.input_terminals["TestName"];

        var outputTerminal = new Terminals.OutputTerminal({ name: "TestOuptut", datatypes: ["txt"] });
        outputTerminal.node = {
            markChanged: function() {},
            post_job_actions: [],
            hasMappedOverInputTerminals: function() {
                return false;
            },
            hasConnectedOutputTerminals: function() {
                return true;
            }
        };
        outputTerminal.terminalMapping = {
            disableMapOver: function() {},
            mapOver: new Terminals.CollectionTypeDescription("list")
        };
        var c = new Connector(outputTerminal, terminal);

        return c;
    },
    connectAttachedMappedOutput: function() {
        this.view.addDataInput({ name: "TestName", extensions: ["txt"], input_type: "dataset_collection" });
        var terminal = this.view.node.input_terminals["TestName"];

        var outputTerminal = new Terminals.OutputTerminal({ name: "TestOuptut", datatypes: ["txt"] });
        outputTerminal.node = {
            markChanged: function() {},
            post_job_actions: [],
            hasMappedOverInputTerminals: function() {
                return false;
            },
            hasConnectedOutputTerminals: function() {
                return true;
            }
        };
        outputTerminal.terminalMapping = {
            disableMapOver: function() {},
            mapOver: new Terminals.CollectionTypeDescription("list")
        };
        var c = new Connector(outputTerminal, terminal);

        return c;
    }
});

QUnit.test("tool error styling", function(assert) {
    this.set_for_node({ errors: false });
    this.view.render();
    assert.ok(!this.view.$el.hasClass("tool-node-error"));
    this.set_for_node({ errors: true });
    this.view.render();
    assert.ok(this.view.$el.hasClass("tool-node-error"));
});

QUnit.test("rendering correct width", function(assert) {
    // Default width is 150
    this.view.render();
    assert.equal(this.view.$el.width(), 150);

    // If any data rows are greater, it will update
    this.view.updateMaxWidth(200);
    this.view.render();
    assert.equal(this.view.$el.width(), 200);

    // However 250 is the maximum width of node
    this.view.updateMaxWidth(300);
    this.view.render();
    assert.equal(this.view.$el.width(), 250);
});

QUnit.test("replacing terminal on data input update preserves connections", function(assert) {
    var connector = this.connectAttachedTerminal("txt", "txt");
    var newElement = $("<div class='inputs'></div>");
    this.view.addDataInput({ name: "TestName", extensions: ["txt"] }, newElement);
    var terminal = newElement.find(".input-terminal")[0].terminal;
    assert.ok(connector.handle2 === terminal);
});

QUnit.test("replacing terminal on data multiple input update preserves collection connections", function(assert) {
    var connector = this.connectAttachedMultiInputTerminal("txt", "txt");
    var connector_destroy_spy = sinon.spy(connector, "destroy");
    var newElement = $("<div class='inputs'></div>");
    this.view.addDataInput({ name: "TestName", extensions: ["txt"], multiple: true }, newElement);
    assert.ok(!connector_destroy_spy.called);
});

QUnit.test("replacing mapped terminal on data collection input update preserves connections", function(assert) {
    var connector = this.connectAttachedMappedOutput();
    var newElement = $("<div class='inputs'></div>");
    this.view.addDataInput({ name: "TestName", extensions: ["txt"], input_type: "dataset_collection" }, newElement);
    var terminal = newElement.find(".input-terminal")[0].terminal;
    assert.ok(connector.handle2 === terminal);
});

QUnit.test("replacing terminal on data input destroys invalid connections", function(assert) {
    var connector = this.connectAttachedTerminal("txt", "txt");
    var newElement = $("<div class='inputs'></div>");
    var connector_destroy_spy = sinon.spy(connector, "destroy");
    // Replacing input with same name - but now of type bam should destroy connection.
    this.view.addDataInput({ name: "TestName", extensions: ["bam"] }, newElement);
    var terminal = newElement.find(".input-terminal")[0].terminal;
    assert.ok(connector_destroy_spy.called);
});

QUnit.test("replacing terminal on data input with collection changes mapping view type", function(assert) {
    var connector = this.connectAttachedTerminal("txt", "txt");
    var newElement = $("<div class='inputs'></div>");
    var connector_destroy_spy = sinon.spy(connector, "destroy");
    this.view.addDataInput({ name: "TestName", extensions: ["txt"], input_type: "dataset_collection" }, newElement);
    // Input type changed to dataset_collection - old connections are reset.
    // Would be nice to preserve these connections and make them map over.
    var terminal = newElement.find(".input-terminal")[0].terminal;
    assert.ok(connector_destroy_spy.called);
});

QUnit.test("replacing terminal on data collection input with simple input changes mapping view type", function(assert) {
    var connector = this.connectAttachedMappedOutput();
    var newElement = $("<div class='inputs'></div>");
    var connector_destroy_spy = sinon.spy(connector, "destroy");
    this.view.addDataInput({ name: "TestName", extensions: ["txt"], input_type: "dataset" }, newElement);
    var terminal = newElement.find(".input-terminal")[0].terminal;
    assert.ok(connector_destroy_spy.called);
});

// global InputTerminalView
QUnit.module("Input terminal view", {
    beforeEach: function() {
        this.node = { input_terminals: [] };
        this.input = { name: "i1", extensions: "txt", multiple: false };
        this.view = new TerminalsView.InputTerminalView({
            node: this.node,
            input: this.input
        });
    }
});

QUnit.test("terminal added to node", function(assert) {
    assert.ok(this.node.input_terminals.i1);
    assert.equal(this.node.input_terminals.i1.datatypes, ["txt"]);
    assert.equal(this.node.input_terminals.i1.multiple, false);
});

QUnit.test("terminal element", function(assert) {
    var el = this.view.el;
    assert.equal(el.tagName, "DIV");
    assert.equal(el.className, "terminal input-terminal");
});

// global OutputTerminalView
QUnit.module("Output terminal view", {
    beforeEach: function() {
        this.node = { output_terminals: [] };
        this.output = { name: "o1", extensions: "txt" };
        this.view = new TerminalsView.OutputTerminalView({
            node: this.node,
            output: this.output
        });
    }
});

QUnit.test("terminal added to node", function(assert) {
    assert.ok(this.node.output_terminals.o1);
    assert.equal(this.node.output_terminals.o1.datatypes, ["txt"]);
});

QUnit.test("terminal element", function(assert) {
    var el = this.view.el;
    assert.equal(el.tagName, "DIV");
    assert.equal(el.className, "terminal output-terminal");
});

QUnit.module("CollectionTypeDescription", {
    listType: function() {
        return new Terminals.CollectionTypeDescription("list");
    },
    pairedType: function() {
        return new Terminals.CollectionTypeDescription("paired");
    },
    pairedListType: function() {
        return new Terminals.CollectionTypeDescription("list:paired");
    }
});

QUnit.test("canMatch", function(assert) {
    assert.ok(this.listType().canMatch(this.listType()));
    assert.ok(!this.listType().canMatch(this.pairedType()));
    assert.ok(!this.listType().canMatch(this.pairedListType()));
});

QUnit.test("canMatch special types", function(assert) {
    assert.ok(this.listType().canMatch(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.canMatch(this.pairedListType()));

    assert.ok(!this.listType().canMatch(Terminals.NULL_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(!Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.canMatch(this.pairedListType()));
});

QUnit.test("canMapOver", function(assert) {
    assert.ok(!this.listType().canMapOver(this.listType()));
    assert.ok(!this.listType().canMapOver(this.pairedType()));
    assert.ok(this.pairedListType().canMapOver(this.pairedType()));
    assert.ok(!this.listType().canMapOver(this.pairedListType()));
});

QUnit.test("canMapOver special types", function(assert) {
    assert.ok(!this.listType().canMapOver(Terminals.NULL_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(!Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.canMapOver(this.pairedListType()));

    // Following two should be able to be relaxed someday maybe - but the
    // tracking gets tricky I think. For now mapping only works for explicitly
    // defined collection types.
    assert.ok(!this.listType().canMapOver(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(!Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.canMapOver(this.pairedListType()));
});

QUnit.test("append", function(assert) {
    var appendedType = this.listType().append(this.pairedType());
    assert.equal(appendedType.collectionType, "list:paired");
});

QUnit.test("isCollection", function(assert) {
    assert.ok(this.listType().isCollection);
    assert.ok(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.isCollection);
    assert.ok(!Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.isCollection);
});

QUnit.test("equal", function(assert) {
    assert.ok(!this.listType().equal(this.pairedType()));
    assert.ok(this.listType().equal(this.listType()));

    assert.ok(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.equal(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(!Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.equal(Terminals.NULL_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(!Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.equal(this.pairedType()));
    assert.ok(!this.pairedType().equal(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION));

    assert.ok(Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.equal(Terminals.NULL_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(!Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.equal(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(!Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.equal(this.listType()));
    assert.ok(!this.listType().equal(Terminals.NULL_COLLECTION_TYPE_DESCRIPTION));
});

QUnit.module("TerminalMapping", {
    beforeEach: function() {
        testApp.create();
    },
    afterEach: function() {
        testApp.destroy();
    }
});

QUnit.test("default constructor", function(assert) {
    var terminal = {};
    var mapping = new Terminals.TerminalMapping({ terminal: terminal });
    assert.ok(terminal.terminalMapping === mapping);
    assert.ok(mapping.mapOver === Terminals.NULL_COLLECTION_TYPE_DESCRIPTION);
});

QUnit.test("constructing with mapOver", function(assert) {
    var terminal = {};
    var mapping = new Terminals.TerminalMapping({
        terminal: terminal,
        mapOver: new Terminals.CollectionTypeDescription("list")
    });
    assert.ok(mapping.mapOver.collectionType == "list");
});

QUnit.test("disableMapOver", function(assert) {
    var terminal = {};
    var mapping = new Terminals.TerminalMapping({
        terminal: terminal,
        mapOver: new Terminals.CollectionTypeDescription("list")
    });
    var changeSpy = sinon.spy();
    mapping.bind("change", changeSpy);
    mapping.disableMapOver();
    assert.ok(mapping.mapOver === Terminals.NULL_COLLECTION_TYPE_DESCRIPTION);
    assert.ok(changeSpy.called);
});

QUnit.module("terminal mapping logic", {
    beforeEach: function() {
        testApp.create();
    },
    afterEach: function() {
        testApp.destroy();
        if (this.inputTerminal1) {
            this.inputTerminal1.element.remove();
        }
    },
    newInputTerminal: function(mapOver, input, node) {
        input = input || {};
        node = node || this.newNode();
        if (!("extensions" in input)) {
            input["extensions"] = ["data"];
        }
        var inputEl = $("<div>")[0];
        var inputTerminal = new Terminals.InputTerminal({ element: inputEl, input: input });
        var inputTerminalMapping = new Terminals.TerminalMapping({ terminal: inputTerminal });
        inputTerminal.node = node;
        if (mapOver) {
            inputTerminal.setMapOver(new Terminals.CollectionTypeDescription(mapOver));
        }
        return inputTerminal;
    },
    newInputCollectionTerminal: function(input, node) {
        input = input || {};
        node = node || this.newNode();
        if (!("extensions" in input)) {
            input["extensions"] = ["data"];
        }
        var inputEl = $("<div>")[0];
        var inputTerminal = new Terminals.InputCollectionTerminal({ element: inputEl, input: input });
        var inputTerminalMapping = new Terminals.TerminalMapping({ terminal: inputTerminal });
        inputTerminal.node = node;
        return inputTerminal;
    },
    newOutputTerminal: function(mapOver, output, node) {
        output = output || {};
        node = node || this.newNode();
        if (!("extensions" in output)) {
            output["extensions"] = ["data"];
        }
        var outputEl = $("<div>")[0];
        var outputTerminal = new Terminals.OutputTerminal({ element: outputEl, datatypes: output.extensions });
        var outputTerminalMapping = new Terminals.TerminalMapping({ terminal: outputTerminal });
        outputTerminal.node = node;
        if (mapOver) {
            outputTerminal.setMapOver(new Terminals.CollectionTypeDescription(mapOver));
        }
        return outputTerminal;
    },
    newOutputCollectionTerminal: function(collectionType, output, node, mapOver) {
        collectionType = collectionType || "list";
        output = output || {};
        node = node || this.newNode();
        if (!("extensions" in output)) {
            output["extensions"] = ["data"];
        }
        var outputEl = $("<div>")[0];
        var outputTerminal = new Terminals.OutputCollectionTerminal({
            element: outputEl,
            datatypes: output.extensions,
            collection_type: collectionType
        });
        var outputTerminalMapping = new Terminals.TerminalMapping({ terminal: outputTerminal });
        outputTerminal.node = node;
        if (mapOver) {
            outputTerminal.setMapOver(new Terminals.CollectionTypeDescription(mapOver));
        }
        return outputTerminal;
    },
    newNode: function() {
        var nodeEl = $("<div>")[0];
        var node = new Node(create_app(), { element: nodeEl });
        return node;
    },
    _addExistingOutput: function(terminal, output, connected) {
        var self = this;
        var node = terminal.node;
        if (connected) {
            var inputTerminal = self.newInputTerminal();
            new Connector(inputTerminal, output);
        }
        this._addTerminalTo(output, node.output_terminals);
        return output;
    },
    addOutput: function(terminal, connected) {
        var connectedOutput = this.newOutputTerminal();
        return this._addExistingOutput(terminal, connectedOutput, connected);
    },
    addCollectionOutput: function(terminal, connected) {
        var collectionOutput = this.newOutputCollectionTerminal();
        return this._addExistingOutput(terminal, collectionOutput, connected);
    },
    addConnectedOutput: function(terminal) {
        return this.addOutput(terminal, true);
    },
    addConnectedCollectionOutput: function(terminal) {
        var connectedOutput = this.newOutputCollectionTerminal();
        return this._addExistingOutput(terminal, connectedOutput, true);
    },
    addConnectedInput: function(terminal) {
        var self = this;
        var connectedInput = this.newInputTerminal();
        var node = terminal.node;
        var outputTerminal = self.newOutputTerminal();
        new Connector(connectedInput, outputTerminal);
        this._addTerminalTo(connectedInput, node.input_terminals);
        return connectedInput;
    },
    _addTerminalTo: function(terminal, terminals) {
        var name = "other";
        while (name in terminals) {
            name += "_";
        }
        terminals[name] = terminal;
    },
    verifyNotAttachable: function(assert, inputTerminal, output) {
        var outputTerminal;
        if (typeof output == "string") {
            // Just given a collection type... create terminal out of it.
            outputTerminal = this.newOutputTerminal(output);
        } else {
            outputTerminal = output;
        }

        assert.ok(!inputTerminal.attachable(outputTerminal));
    },
    verifyAttachable: function(assert, inputTerminal, output) {
        var outputTerminal;
        if (typeof output == "string") {
            // Just given a collection type... create terminal out of it.
            outputTerminal = this.newOutputTerminal(output);
        } else {
            outputTerminal = output;
        }

        assert.ok(inputTerminal.attachable(outputTerminal), "Cannot attach " + outputTerminal + " to " + inputTerminal);

        // Go further... make sure datatypes are being enforced
        inputTerminal.datatypes = ["bam"];
        outputTerminal.datatypes = ["txt"];
        assert.ok(!inputTerminal.attachable(outputTerminal));
    },
    verifyMappedOver: function(assert, terminal) {
        assert.ok(terminal.terminalMapping.mapOver.isCollection);
    },
    verifyNotMappedOver: function(assert, terminal) {
        assert.ok(!terminal.terminalMapping.mapOver.isCollection);
    }
});

QUnit.test("unconstrained input can be mapped over", function(assert) {
    this.inputTerminal1 = this.newInputTerminal();
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("unmapped input can be mapped over if matching connected input terminals map type", function(assert) {
    this.inputTerminal1 = this.newInputTerminal();
    var connectedInput1 = this.addConnectedInput(this.inputTerminal1);
    var connectedInput2 = this.addConnectedInput(this.inputTerminal1);
    connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("unmapped input cannot be mapped over if not matching connected input terminals map type", function(assert) {
    this.inputTerminal1 = this.newInputTerminal();
    var connectedInput = this.addConnectedInput(this.inputTerminal1);
    connectedInput.setMapOver(new Terminals.CollectionTypeDescription("paired"));
    this.verifyNotAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test(
    "unmapped input can be attached to by output collection if matching connected input terminals map type",
    function(assert) {
        this.inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput(this.inputTerminal1);
        var connectedInput2 = this.addConnectedInput(this.inputTerminal1);
        connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list"));
        var outputTerminal = this.newOutputCollectionTerminal("list");
        this.verifyAttachable(assert, this.inputTerminal1, outputTerminal);
    }
);

QUnit.test(
    "unmapped input cannot be attached to by output collection if matching connected input terminals don't match map type",
    function(assert) {
        this.inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput(this.inputTerminal1);
        var connectedInput2 = this.addConnectedInput(this.inputTerminal1);
        connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list"));
        var outputTerminal = this.newOutputCollectionTerminal("paired");
        this.verifyNotAttachable(assert, this.inputTerminal1, outputTerminal);
    }
);

QUnit.test(
    "unmapped input can be attached to by output collection if effective output type (output+mapover) is same as mapped over input",
    function(assert) {
        this.inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput(this.inputTerminal1);
        var connectedInput2 = this.addConnectedInput(this.inputTerminal1);
        connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list:paired"));
        var outputTerminal = this.newOutputCollectionTerminal("paired");
        outputTerminal.setMapOver(new Terminals.CollectionTypeDescription("list"));
        this.verifyAttachable(assert, this.inputTerminal1, outputTerminal);
    }
);

QUnit.test(
    "unmapped input cannot be attached to by output collection if effective output type (output+mapover) is not same as mapped over input (1)",
    function(assert) {
        this.inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput(this.inputTerminal1);
        var connectedInput2 = this.addConnectedInput(this.inputTerminal1);
        connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list:paired"));
        var outputTerminal = this.newOutputCollectionTerminal("list");
        outputTerminal.setMapOver(new Terminals.CollectionTypeDescription("list"));
        this.verifyNotAttachable(assert, this.inputTerminal1, outputTerminal);
    }
);

QUnit.test(
    "unmapped input cannot be attached to by output collection if effective output type (output+mapover) is not same as mapped over input (2)",
    function(assert) {
        this.inputTerminal1 = this.newInputTerminal();
        var connectedInput1 = this.addConnectedInput(this.inputTerminal1);
        var connectedInput2 = this.addConnectedInput(this.inputTerminal1);
        connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list:paired"));
        var outputTerminal = this.newOutputCollectionTerminal("list");
        outputTerminal.setMapOver(new Terminals.CollectionTypeDescription("paired"));
        this.verifyNotAttachable(assert, this.inputTerminal1, outputTerminal);
    }
);

QUnit.test("unmapped input with unmapped, connected outputs cannot be mapped over", function(assert) {
    // It would invalidate the connections - someday maybe we could try to
    // recursively map over everything down the DAG - it would be expensive
    // to check that though.
    this.inputTerminal1 = this.newInputTerminal();
    this.addConnectedOutput(this.inputTerminal1);
    this.verifyNotAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("unmapped input with connected mapped outputs can be mapped over if matching", function(assert) {
    // It would invalidate the connections - someday maybe we could try to
    // recursively map over everything down the DAG - it would be expensive
    // to check that though.
    this.inputTerminal1 = this.newInputTerminal();
    var connectedOutput = this.addConnectedOutput(this.inputTerminal1);
    connectedOutput.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("unmapped input with connected mapped outputs cannot be mapped over if mapover not matching", function(
    assert
) {
    // It would invalidate the connections - someday maybe we could try to
    // recursively map over everything down the DAG - it would be expensive
    // to check that though.
    this.inputTerminal1 = this.newInputTerminal();
    var connectedOutput = this.addConnectedOutput(this.inputTerminal1);
    connectedOutput.setMapOver(new Terminals.CollectionTypeDescription("paired"));
    this.verifyNotAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("explicitly constrained input can not be mapped over by incompatible collection type", function(assert) {
    this.inputTerminal1 = this.newInputTerminal();
    this.inputTerminal1.setMapOver(new Terminals.CollectionTypeDescription("paired"));
    this.verifyNotAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("explicitly constrained input can be mapped over by compatible collection type", function(assert) {
    this.inputTerminal1 = this.newInputTerminal();
    this.inputTerminal1.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("unconstrained collection input can be mapped over", function(assert) {
    this.inputTerminal1 = this.newInputCollectionTerminal({ collection_types: ["paired"] });
    this.verifyAttachable(assert, this.inputTerminal1, "list:paired");
});

QUnit.test("unconstrained collection input cannot be mapped over by incompatible type", function(assert) {
    this.inputTerminal1 = this.newInputCollectionTerminal({ collection_types: ["list"] }); // Would need to be paired...
    this.verifyNotAttachable(assert, this.inputTerminal1, "list:paired");
});

QUnit.test("explicitly mapped over collection input can be attached by explicit mapping", function(assert) {
    this.inputTerminal1 = this.newInputCollectionTerminal({ collection_types: ["paired"] });
    this.inputTerminal1.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.verifyAttachable(assert, this.inputTerminal1, "list:paired");
});

QUnit.test("explicitly mapped over collection input can be attached by explicit mapping", function(assert) {
    this.inputTerminal1 = this.newInputCollectionTerminal({ collection_types: ["list:paired"] });
    this.inputTerminal1.setMapOver(new Terminals.CollectionTypeDescription("list"));
    // effectively input is list:list:paired so shouldn't be able to attach
    this.verifyNotAttachable(assert, this.inputTerminal1, "list:paired");
});

QUnit.test("unconnected multiple inputs can be connected to rank 1 collections", function(assert) {
    this.inputTerminal1 = this.newInputTerminal(null, { multiple: true });
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("multiple input attachable by collections", function(assert) {
    this.inputTerminal1 = this.newInputTerminal(null, { multiple: true });
    var connectedInput1 = this.addConnectedInput(this.inputTerminal1);
    this.addConnectedOutput(connectedInput1);
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("unconnected multiple inputs cannot be connected to rank > 1 collections (yet...)", function(assert) {
    this.inputTerminal1 = this.newInputTerminal(null, { multiple: true });
    this.verifyNotAttachable(assert, this.inputTerminal1, "list:paired");
});

QUnit.test("resetMappingIfNeeded does nothing if not mapped", function(assert) {
    this.inputTerminal1 = this.newInputTerminal();
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyNotMappedOver(assert, this.inputTerminal1);
});

QUnit.test("resetMappingIfNeeded resets unconstrained input", function(assert) {
    this.inputTerminal1 = this.newInputTerminal("list");
    this.verifyMappedOver(assert, this.inputTerminal1);
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyNotMappedOver(assert, this.inputTerminal1);
});

QUnit.test("resetMappingIfNeeded does not reset if connected output depends on being mapped", function(assert) {
    this.inputTerminal1 = this.newInputTerminal("list");
    var connectedOutput = this.addConnectedOutput(this.inputTerminal1);
    connectedOutput.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyMappedOver(assert, this.inputTerminal1);
});

QUnit.test("resetMappingIfNeeded resets if node outputs are not connected to anything", function(assert) {
    this.inputTerminal1 = this.newInputTerminal("list");
    var output = this.addOutput(this.inputTerminal1);
    output.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyNotMappedOver(assert, this.inputTerminal1);
});

QUnit.test("resetMappingIfNeeded an input resets node outputs if they not connected to anything", function(assert) {
    this.inputTerminal1 = this.newInputTerminal("list");
    var output = this.addOutput(this.inputTerminal1);
    output.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyNotMappedOver(assert, output);
});

QUnit.test("resetMappingIfNeeded an input resets node collection outputs if they not connected to anything", function(
    assert
) {
    this.inputTerminal1 = this.newInputTerminal("list");
    var output = this.addCollectionOutput(this.inputTerminal1);
    output.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyNotMappedOver(assert, output);
});

QUnit.test("resetMappingIfNeeded resets if not last mapped over input", function(assert) {
    // Idea here is that other nodes are forcing output to still be mapped
    // over so don't need to disconnect output nodes.
    this.inputTerminal1 = this.newInputTerminal("list");
    var connectedInput1 = this.addConnectedInput(this.inputTerminal1);
    connectedInput1.setMapOver(new Terminals.CollectionTypeDescription("list"));
    var connectedOutput = this.addConnectedOutput(this.inputTerminal1);
    connectedOutput.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.inputTerminal1.resetMappingIfNeeded();
    // inputTerminal1 can be reset because connectedInput1
    // is still forcing connectedOutput to be mapped over,
    // so verify inputTerminal1 is rest and connectedInput1
    // and connectedOutput are untouched.
    this.verifyNotMappedOver(assert, this.inputTerminal1);
    this.verifyMappedOver(assert, connectedInput1);
    this.verifyMappedOver(assert, connectedOutput);
});

QUnit.test("simple mapping over collection outputs works correctly", function(assert) {
    this.inputTerminal1 = this.newInputTerminal();
    var connectedOutput = this.addConnectedCollectionOutput(this.inputTerminal1);
    this.inputTerminal1.setMapOver(new Terminals.CollectionTypeDescription("list"));

    // Can attach list output of collection type list that is being mapped
    // over another list to a list:list (because this is what it is) but not
    // to a list:list:list.
    var testTerminal2 = this.newInputTerminal("list:list");
    this.verifyAttachable(assert, testTerminal2, connectedOutput);

    var testTerminal1 = this.newInputTerminal("list:list:list");
    this.verifyNotAttachable(assert, testTerminal1, connectedOutput);
});
