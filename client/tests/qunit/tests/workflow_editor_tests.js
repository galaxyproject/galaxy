/* global QUnit */
import $ from "jquery";
import { testDatatypesMapper } from "components/Datatypes/test_fixtures";
import sinon from "sinon";
import WorkflowNode from "components/Workflow/Editor/Node";
import Terminals from "components/Workflow/Editor/modules/terminals";
import { InputDragging, OutputDragging } from "components/Workflow/Editor/modules/dragging";
import Connector from "components/Workflow/Editor/modules/connector";
import Vue from "vue";

// create body template and
const createApp = function () {
    $("body").append(
        `<div id="canvas-viewport">
            <div id="canvas-container"/>
            <div id="overview">
            <canvas id="overview-canvas"/>
            <div id="overview-viewport"/>
            </div>`
    );
};

const nodeData = {
    inputs: [],
    outputs: [{ name: "out1", extensions: ["data"] }],
    config_form: "{}",
    tool_state: "ok",
    tool_errors: false,
    tooltip: "tool tooltip",
    annotation: "tool annotation",
    workflow_outputs: [{ output_name: "out1" }],
    label: "Cat that data.",
};

class Node {
    constructor(attr = {}) {
        this.element = attr.element;
        this.postJobActions = {};
        this.inputTerminals = {};
        this.outputTerminals = {};
    }
}

function buildNode(propsData) {
    const component = Vue.extend(WorkflowNode);
    propsData.step = {};
    propsData.getManager = () => {
        return {};
    };
    propsData.getCanvasManager = () => {
        return {};
    };
    propsData.datatypesMapper = testDatatypesMapper;
    return new component({
        propsData: propsData,
        el: "#canvas-container",
    });
}

QUnit.module("Input terminal model test", {
    beforeEach: function () {
        createApp();
        this.node = new Node();
        this.input = { extensions: ["txt"], multiple: false, optional: false };
        const inputEl = $("<div>")[0];
        this.input_terminal = new Terminals.InputTerminal({
            datatypesMapper: testDatatypesMapper,
            element: inputEl,
            input: this.input,
            node: this.node,
        });
    },
    afterEach: function () {
        delete this.node;
    },
    multiple: function () {
        this.input.multiple = true;
        this.input_terminal.update(this.input);
    },
    test_connector: function () {
        const inputEl = $("<div>")[0];
        const outputTerminal = new Terminals.OutputTerminal({
            element: inputEl,
            datatypes: ["input"],
            input: {},
            node: this.node,
        });
        const inputTerminal = this.input_terminal;
        return new Connector({}, outputTerminal, inputTerminal);
    },
    with_test_connector: function (f) {
        this.test_connector();
        f();
        this.reset_connectors();
    },
    reset_connectors: function () {
        this.input_terminal.connectors = [];
    },
    test_accept: function (other) {
        other = other || { node: {}, datatypes: ["txt"], optional: false };
        if (!other.mapOver) {
            other.mapOver = function () {
                return Terminals.NULL_COLLECTION_TYPE_DESCRIPTION;
            };
        }
        return this.input_terminal.canAccept(other).canAccept;
    },
});

QUnit.test("test update", function (assert) {
    assert.deepEqual(this.input_terminal.datatypes, ["txt"]);
    assert.equal(this.input_terminal.multiple, false);
    this.input_terminal.update({ extensions: ["bam"], multiple: true });
    assert.deepEqual(this.input_terminal.datatypes, ["bam"]);
    assert.equal(this.input_terminal.multiple, true);
});

QUnit.test("test connect", function (assert) {
    const connector = { name: "connector" };
    const changeSpy = sinon.spy();
    this.input_terminal.on("change", changeSpy);
    this.input_terminal.connect(connector);
    assert.ok(this.input_terminal.connectors[0].name === "connector");
});

QUnit.test("test disconnect", function (assert) {
    const connector = this.test_connector();
    const changeSpy = sinon.spy();
    this.input_terminal.on("change", changeSpy);
    this.input_terminal.disconnect(connector);
    assert.equal(this.input_terminal.connectors.length, 0);
});

QUnit.test("test redraw", function (assert) {
    const connector = this.test_connector();
    connector.redraw = sinon.spy();
    this.input_terminal.redraw();
    // Assert connectors were redrawn
    assert.ok(connector.redraw.called);
});

QUnit.test("test destroy", function (assert) {
    const connector = this.test_connector();
    connector.destroy = sinon.spy();
    this.input_terminal.destroy();
    // Assert connectors were destroyed
    assert.ok(connector.destroy.called);
});

QUnit.test("can accept exact datatype", function (assert) {
    const other = { node: {}, datatypes: ["txt"] }; // input also txt
    assert.ok(this.test_accept(other));
});

QUnit.test("can accept subclass datatype", function (assert) {
    const other = { node: {}, datatypes: ["tabular"] }; // tabular subclass of input txt
    assert.ok(this.test_accept(other));
});

QUnit.test("cannot accept incorrect datatype", function (assert) {
    const other = { node: {}, datatypes: ["binary"] }; // binary is not txt
    assert.ok(!this.test_accept(other));
});

QUnit.test("can accept inputs", function (assert) {
    // Other is data input module - always accept (currently - could be
    // more intelligent by looking at what else input is connected to.
    const other = { node: {}, datatypes: ["input"] };
    assert.ok(this.test_accept(other));
});

QUnit.test("can't connect non-optional", function (assert) {
    const other = { node: {}, datatypes: ["input"], optional: true };
    assert.ok(!this.test_accept(other));
});

QUnit.test("multiple inputs can accept optional outputs regardless", function (assert) {
    // Galaxy multiple inputs have an optional field but it is hard to resolve that
    // completely until runtime.
    const other = { node: {}, datatypes: ["input"], optional: true };
    this.multiple();
    assert.ok(this.test_accept(other));
});

QUnit.test("input type can accept any datatype", function (assert) {
    this.input.extensions = ["input"];
    this.input_terminal.update(this.input);
    const other = { node: {}, datatypes: ["binary"] };
    assert.ok(this.test_accept(other));
});

QUnit.test("cannot accept when already connected", function (assert) {
    // If other is subtype but already connected, cannot accept
    this.with_test_connector(() => {
        assert.ok(!this.test_accept());
    });
});

QUnit.test("can accept already connected inputs if input is multiple", function (assert) {
    this.multiple();
    this.with_test_connector(() => {
        assert.ok(this.test_accept());
    });
});

QUnit.test("cannot accept already connected inputs if input is multiple but datatypes don't match", function (assert) {
    const other = { node: {}, datatypes: ["binary"] }; // binary is not txt
    this.multiple();
    this.with_test_connector(() => {
        assert.ok(!this.test_accept(other));
    });
});

QUnit.test("can accept list collection for multiple input parameters if datatypes match", function (assert) {
    this.multiple();
    assert.ok(this.test_accept());
});

QUnit.test("can accept list collection for empty multiple inputs", function (assert) {
    const other = {
        node: {},
        datatypes: ["tabular"],
        mapOver: new Terminals.CollectionTypeDescription("list"),
    };
    this.multiple();
    assert.ok(this.test_accept(other));
});

QUnit.test("cannot accept list collection for multiple input if collection already connected", function (assert) {
    const other = {
        node: {},
        datatypes: ["tabular"],
        mapOver: new Terminals.CollectionTypeDescription("list"),
    };
    this.multiple();
    this.with_test_connector(() => {
        assert.ok(!this.test_accept(other));
    });
});

QUnit.module("Connector test", {});

QUnit.test("connects only if both valid handles", function (assert) {
    const input = { connect: sinon.spy() };
    const output = { connect: sinon.spy() };
    new Connector({}, input, null);
    new Connector({}, null, output);
    // Not attempts to connect...
    assert.ok(!input.connect.called);
    assert.ok(!output.connect.called);
    new Connector({}, input, output);
    assert.ok(input.connect.called);
    assert.ok(output.connect.called);
});

QUnit.test("default attributes", function (assert) {
    const input = { connect: sinon.spy() };
    const output = { connect: sinon.spy() };
    const connector = new Connector({}, input, output);
    assert.equal(connector.dragging, false);
    assert.equal(connector.svg.attr("class"), "ribbon");
});

QUnit.test("destroy", function (assert) {
    const input = { connect: sinon.spy(), disconnect: sinon.spy() };
    const output = { connect: sinon.spy(), disconnect: sinon.spy() };
    const connector = new Connector({}, input, output);
    connector.destroy();
    assert.ok(input.disconnect.called);
    assert.ok(output.disconnect.called);
});

QUnit.test("initial redraw", function (assert) {
    const input = {
        connect: sinon.spy(),
        element: $("<div>"),
        isMappedOver: function () {
            return false;
        },
    };
    const output = {
        connect: sinon.spy(),
        element: $("<div>"),
        isMappedOver: function () {
            return false;
        },
    };
    const n = $("#canvas-container").find("svg").length;
    const connector = new Connector({}, input, output);
    // Ensure canvas gets set
    assert.ok(connector.canvas);
    // Ensure it got added to canvas container
    assert.equal(n + 1, $("#canvas-container").find("svg").length);
});

QUnit.module("Input collection terminal model test", {
    beforeEach: function () {
        createApp();
        this.node = new Node();
        this.input = { extensions: ["txt"], collection_types: ["list"] };
        const inputEl = $("<div>")[0];
        this.input_terminal = new Terminals.InputCollectionTerminal({
            datatypesMapper: testDatatypesMapper,
            element: inputEl,
            input: this.input,
            node: this.node,
        });
    },
    afterEach: function () {
        delete this.node;
    },
});

QUnit.test("Collection output can connect to same collection input type", function (assert) {
    const inputTerminal = this.input_terminal;
    const outputTerminal = new Terminals.OutputCollectionTerminal({
        datatypes: ["txt"],
        collection_type: "list",
        node: {},
    });
    outputTerminal.node = { postJobActions: {} };
    assert.ok(
        inputTerminal.canAccept(outputTerminal).canAccept,
        "Input terminal " + inputTerminal + " can not accept " + outputTerminal
    );
});

QUnit.test("Optional collection output can not connect to required collection input", function (assert) {
    const inputTerminal = this.input_terminal;
    const outputTerminal = new Terminals.OutputCollectionTerminal({
        datatypes: ["txt"],
        collection_type: "list",
        optional: true,
        node: {},
    });
    outputTerminal.node = {};
    assert.ok(!inputTerminal.canAccept(outputTerminal).canAccept);
});

QUnit.test("Collection output cannot connect to different collection input type", function (assert) {
    const inputTerminal = this.input_terminal;
    const outputTerminal = new Terminals.OutputCollectionTerminal({
        datatypes: ["txt"],
        collection_type: "paired",
        node: {},
    });
    outputTerminal.node = {};
    assert.ok(!inputTerminal.canAccept(outputTerminal).canAccept);
});

QUnit.module("Node unit test", {
    beforeEach: function () {
        this.input_terminal = { destroy: sinon.spy(), redraw: sinon.spy() };
        this.output_terminal = { destroy: sinon.spy(), redraw: sinon.spy() };
        this.node = buildNode({ type: "tool", name: "newnode" });
        this.element = this.node.element;
        this.node.inputTerminals.i1 = this.input_terminal;
        this.node.outputTerminals.o1 = this.output_terminal;
    },
    $: function (selector) {
        return $(this.node.element).find(selector);
    },
    init_field_data_simple: function () {
        const data = {
            inputs: [{ name: "input1", extensions: ["data"] }],
            outputs: [{ name: "output1", extensions: ["data"] }],
            name: "newnode",
            label: null,
        };
        this.node.initData(data);
    },
    update_field_data_with_new_input: function () {
        const data = {
            inputs: [
                { name: "input1", extensions: ["data"] },
                { name: "extra_0|input1", extensions: ["data"] },
            ],
            outputs: [{ name: "output1", extensions: ["data"] }],
            postJobActions: {},
            label: "New Label",
        };
        this.node.setNode(data);
    },
});

QUnit.test("make active", function (assert) {
    assert.ok(this.element.className.indexOf("node-active") == -1);
    this.node.makeActive();
    assert.ok(this.element.className.indexOf("node-active") != -1);
});

QUnit.test("destroy", function (assert) {
    this.node.onRemove();
    assert.ok(this.input_terminal.destroy.called);
    assert.ok(this.output_terminal.destroy.called);
});

QUnit.test("error", function (assert) {
    // Test body of div updated and workflow notified of change.
    const node_changed_spy = sinon.spy(this.node, "setData");
    this.node.initData({ errors: "NODE ERROR", inputs: [], outputs: [] });
    Vue.nextTick(() => {
        const errorText = $(this.node.element).find(".node-error").text().trim();
        assert.equal(errorText, "NODE ERROR");
        assert.ok(node_changed_spy.called);
    });
});

QUnit.test("init_field_data properties", function (assert) {
    const node = this.node;
    const node_changed_spy = sinon.spy(this.node, "setData");
    this.node.initData(nodeData);
    Vue.nextTick(() => {
        assert.equal(node.config_form, "{}");
        assert.equal(node.tool_state, "ok");
        assert.equal(node.tooltip, "tool tooltip");
        assert.equal(node.annotation, "tool annotation");
        assert.equal(node.label, "Cat that data.");
        assert.deepEqual(node.postJobActions, {});
        assert.ok(node.activeOutputs.get("out1"));
        assert.ok(node_changed_spy.called);
    });
});

QUnit.test("init_field_data data", function (assert) {
    // pre-init not tool form body...
    assert.equal(this.$(".output-terminal").length, 0);
    assert.equal(this.$(".input-terminal").length, 0);
    assert.equal(this.$(".rule").length, 0);
    const node_changed_spy = sinon.spy(this.node, "setData");
    this.init_field_data_simple();
    Vue.nextTick(() => {
        assert.ok(node_changed_spy.called);
        assert.equal(this.$(".output-terminal").length, 1);
        assert.equal(this.$(".input-terminal").length, 1);
        assert.equal(this.$(".rule").length, 1);
        assert.equal(this.$(".node-title").text(), "newnode");
        assert.ok(this.$(".node-header").find("i").hasClass("fa-wrench"));
    });
});

QUnit.test("node title behavior", function (assert) {
    assert.equal(this.$(".node-title").text(), "newnode");
    const node_changed_spy = sinon.spy(this.node, "setData");
    this.init_field_data_simple();
    this.update_field_data_with_new_input();
    Vue.nextTick(() => {
        assert.equal(this.$(".node-title").text(), "New Label");
        assert.ok(node_changed_spy.called);
    });
});

QUnit.test("update_field_data updated data inputs and outputs", function (assert) {
    const node_changed_spy = sinon.spy(this.node, "setData");
    // Call init with one input and output.
    this.init_field_data_simple();
    this.update_field_data_with_new_input();
    Vue.nextTick(() => {
        // Now there are 2 inputs...
        assert.equal(this.$(".input-terminal").length, 2);
        assert.equal(this.$(".output-terminal").length, 1);
        assert.equal(this.$(".rule").length, 1);
        assert.ok(node_changed_spy.called);
    });
});

QUnit.test("update_field_data preserves connectors", function (assert) {
    const node_changed_spy = sinon.spy(this.node, "onChange");
    // Call init with one input and output.
    this.init_field_data_simple();

    Vue.nextTick(() => {
        const node = this.node;
        const connector = new Connector({});
        const old_input_terminal = node.inputTerminals.input1;
        old_input_terminal.connectors.push(connector);

        // Update node, make sure connector still the same...
        this.update_field_data_with_new_input();
        Vue.nextTick(() => {
            assert.ok(node_changed_spy.called);

            let new_input_terminal = node.inputTerminals.input1;
            assert.equal(connector, new_input_terminal.connectors[0]);

            // Update a second time, make sure connector still the same...
            this.update_field_data_with_new_input();
            Vue.nextTick(() => {
                new_input_terminal = node.inputTerminals.input1;
                assert.equal(connector, new_input_terminal.connectors[0]);
            });
        });
    });
});

QUnit.test("update_field_data destroys old terminals", function (assert) {
    const node = this.node;
    const data = {
        inputs: [
            { name: "input1", extensions: ["data"] },
            { name: "willDisappear", extensions: ["data"] },
        ],
        outputs: [{ name: "output1", extensions: ["data"] }],
    };
    node.initData(data);
    Vue.nextTick(() => {
        const old_input_terminal = node.inputTerminals.willDisappear;
        const destroy_spy = sinon.spy(old_input_terminal, "destroy");
        this.update_field_data_with_new_input();
        Vue.nextTick(() => {
            assert.ok(destroy_spy.called);
        });
    });
});

QUnit.module("Node view", {
    beforeEach: function () {
        this.node = buildNode({ type: "tool", name: "newnode" });
        this.node.initData(nodeData);
    },
    afterEach: function () {
        delete this.node;
    },
    connectAttachedTerminal: function (inputType, outputType, callback) {
        const data = {
            inputs: [{ name: "TestName", extensions: [inputType] }],
            outputs: [],
        };
        this.node.setNode(data);
        Vue.nextTick(() => {
            const terminal = this.node.inputTerminals["TestName"];
            const inputEl = $("<div>")[0];
            const outputTerminal = new Terminals.OutputTerminal({
                name: "TestOutput",
                datatypes: [outputType],
                mapOver: Terminals.NULL_COLLECTION_TYPE_DESCRIPTION,
                element: inputEl,
                node: {},
            });
            outputTerminal.node = {
                markChanged: function () {},
                postJobActions: [],
                inputTerminals: {},
                outputTerminals: {},
                hasMappedOverInputTerminals: function () {
                    return false;
                },
                hasConnectedOutputTerminals: function () {
                    return true;
                },
            };
            callback(new Connector({}, outputTerminal, terminal));
        });
    },
    connectAttachedMultiInputTerminal: function (inputType, outputType, callback) {
        const data = {
            inputs: [{ name: "TestName", extensions: [inputType], multiple: true }],
            outputs: [],
        };
        this.node.setNode(data);
        Vue.nextTick(() => {
            const terminal = this.node.inputTerminals["TestName"];
            const inputEl = $("<div>")[0];
            const outputTerminal = new Terminals.OutputTerminal({
                name: "TestOutput",
                datatypes: ["txt"],
                mapOver: new Terminals.CollectionTypeDescription("list"),
                element: inputEl,
                node: {},
            });
            outputTerminal.node = {
                markChanged: function () {},
                postJobActions: [],
                inputTerminals: {},
                outputTerminals: {},
                hasMappedOverInputTerminals: function () {
                    return false;
                },
                hasConnectedOutputTerminals: function () {
                    return true;
                },
            };
            callback(new Connector({}, outputTerminal, terminal));
        });
    },
    connectAttachedMappedOutput: function (callback) {
        const node = this.node;
        Vue.nextTick(() => {
            const terminal = node.inputTerminals["TestName"];
            const inputEl = $("<div>")[0];
            const outputTerminal = new Terminals.OutputTerminal({
                name: "TestOutput",
                datatypes: ["txt"],
                mapOver: new Terminals.CollectionTypeDescription("list"),
                element: inputEl,
                node: {},
            });
            outputTerminal.node = {
                markChanged: function () {},
                postJobActions: [],
                inputTerminals: {},
                outputTerminals: {},
                hasMappedOverInputTerminals: function () {
                    return false;
                },
                hasConnectedOutputTerminals: function () {
                    return true;
                },
            };
            const connector = new Connector({}, outputTerminal, terminal);
            callback(connector);
        });
    },
});

QUnit.test("replacing terminal on data input update preserves connections", function (assert) {
    this.node.inputs.push({ name: "TestName", extensions: ["txt"] });
    this.connectAttachedTerminal("txt", "txt", (connector) => {
        const terminal = $(this.node.element).find(".input-terminal")[0].terminal;
        assert.ok(connector.inputHandle === terminal);
    });
});

QUnit.test("replacing terminal on data multiple input update preserves collection connections", function (assert) {
    this.node.inputs.push({ name: "TestName", extensions: ["txt"] });
    this.connectAttachedMultiInputTerminal("txt", "txt", (connector) => {
        const connector_destroy_spy = sinon.spy(connector, "destroy");
        const data = {
            inputs: [{ name: "TestName", extensions: ["txt"], multiple: true }],
            outputs: [],
        };
        this.node.setNode(data);
        Vue.nextTick(() => {
            assert.ok(!connector_destroy_spy.called);
        });
    });
});

QUnit.test("replacing mapped terminal on data collection input update preserves connections", function (assert) {
    const node = this.node;
    node.inputs.push({ name: "TestName", extensions: ["txt"], input_type: "dataset_collection" });
    this.connectAttachedMappedOutput((connector) => {
        const terminal = $(this.node.element).find(".input-terminal")[0].terminal;
        const data = {
            inputs: [{ name: "TestName", extensions: ["txt"], input_type: "dataset_collection" }],
            outputs: [],
        };
        node.setNode(data);
        Vue.nextTick(() => {
            assert.ok(connector.inputHandle === terminal);
        });
    });
});

QUnit.test("replacing terminal on data input destroys invalid connections", function (assert) {
    const node = this.node;
    node.inputs.push({ name: "TestName", extensions: ["txt"] });
    this.connectAttachedTerminal("txt", "txt", (connector) => {
        const connector_destroy_spy = sinon.spy(connector, "destroy");
        const data = {
            inputs: [{ name: "TestName", extensions: ["bam"] }],
            outputs: [],
        };
        node.setNode(data);
        Vue.nextTick(() => {
            $(node.element).find(".input-terminal")[0].terminal;
            assert.ok(connector_destroy_spy.called);
        });
    });
});

QUnit.test("replacing terminal on data input with collection changes mapping view type", function (assert) {
    const node = this.node;
    node.inputs.push({ name: "TestName", extensions: ["txt"] });
    this.connectAttachedTerminal("txt", "txt", (connector) => {
        const connector_destroy_spy = sinon.spy(connector, "destroy");
        const data = {
            inputs: [{ name: "TestName", extensions: ["txt"], input_type: "dataset_collection" }],
            outputs: [],
        };
        node.setNode(data);
        Vue.nextTick(() => {
            // Input type changed to dataset_collection - old connections are reset.
            // Would be nice to preserve these connections and make them map over.
            $(node.element).find(".input-terminal")[0].terminal;
            assert.ok(connector_destroy_spy.called);
        });
    });
});

QUnit.test(
    "replacing terminal on data collection input with simple input changes mapping view type",
    function (assert) {
        const node = this.node;
        node.inputs.push({ name: "TestName", extensions: ["txt"], input_type: "parameter" });
        this.connectAttachedMappedOutput((connector) => {
            const connector_destroy_spy = sinon.spy(connector, "destroy");
            const data = {
                inputs: [{ name: "TestName", extensions: ["txt"], input_type: "dataset" }],
                outputs: [],
            };
            node.setNode(data);
            Vue.nextTick(() => {
                $(node.element).find(".input-terminal")[0].terminal;
                assert.ok(connector_destroy_spy.called);
            });
        });
    }
);

// global InputTerminalView
QUnit.module("Input terminal view", {
    beforeEach: function () {
        this.node = buildNode({ type: "tool", name: "newnode" });
        this.input = { name: "i1", extensions: ["txt"], multiple: false };
        this.node.initData({ inputs: [this.input], outputs: [] });
    },
});

QUnit.test("terminal added to node", function (assert) {
    assert.ok(this.node.inputTerminals.i1);
    assert.equal(this.node.inputTerminals.i1.datatypes[0], "txt");
    assert.equal(this.node.inputTerminals.i1.multiple, false);
});

QUnit.test("terminal element", function (assert) {
    const dragging = new InputDragging(
        {},
        {
            el: document.createElement("div"),
            terminal: {},
        }
    );
    assert.equal(dragging.el.tagName, "DIV");
});

QUnit.module("Output terminal view", {
    beforeEach: function () {
        this.node = buildNode({ type: "tool", name: "newnode" });
        this.output = { name: "o1", extensions: ["txt"] };
        this.node.initData({ inputs: [], outputs: [this.output] });
    },
});

QUnit.test("terminal added to node", function (assert) {
    assert.ok(this.node.outputTerminals.o1);
    assert.equal(this.node.outputTerminals.o1.datatypes[0], "txt");
});

QUnit.test("terminal element", function (assert) {
    const dragging = new OutputDragging(
        {},
        {
            el: document.createElement("div"),
            terminal: {},
        }
    );
    assert.equal(dragging.el.tagName, "DIV");
});

QUnit.module("CollectionTypeDescription", {
    listType: function () {
        return new Terminals.CollectionTypeDescription("list");
    },
    pairedType: function () {
        return new Terminals.CollectionTypeDescription("paired");
    },
    pairedListType: function () {
        return new Terminals.CollectionTypeDescription("list:paired");
    },
});

QUnit.test("canMatch", function (assert) {
    assert.ok(this.listType().canMatch(this.listType()));
    assert.ok(!this.listType().canMatch(this.pairedType()));
    assert.ok(!this.listType().canMatch(this.pairedListType()));
});

QUnit.test("canMatch special types", function (assert) {
    assert.ok(this.listType().canMatch(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.canMatch(this.pairedListType()));

    assert.ok(!this.listType().canMatch(Terminals.NULL_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(!Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.canMatch(this.pairedListType()));
});

QUnit.test("canMapOver", function (assert) {
    assert.ok(!this.listType().canMapOver(this.listType()));
    assert.ok(!this.listType().canMapOver(this.pairedType()));
    assert.ok(this.pairedListType().canMapOver(this.pairedType()));
    assert.ok(!this.listType().canMapOver(this.pairedListType()));
});

QUnit.test("canMapOver special types", function (assert) {
    assert.ok(!this.listType().canMapOver(Terminals.NULL_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(!Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.canMapOver(this.pairedListType()));

    // Following two should be able to be relaxed someday maybe - but the
    // tracking gets tricky I think. For now mapping only works for explicitly
    // defined collection types.
    assert.ok(!this.listType().canMapOver(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION));
    assert.ok(!Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.canMapOver(this.pairedListType()));
});

QUnit.test("append", function (assert) {
    const appendedType = this.listType().append(this.pairedType());
    assert.equal(appendedType.collectionType, "list:paired");
});

QUnit.test("isCollection", function (assert) {
    assert.ok(this.listType().isCollection);
    assert.ok(Terminals.ANY_COLLECTION_TYPE_DESCRIPTION.isCollection);
    assert.ok(!Terminals.NULL_COLLECTION_TYPE_DESCRIPTION.isCollection);
});

QUnit.test("equal", function (assert) {
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

QUnit.test("default constructor", function (assert) {
    const terminal = new Terminals.InputTerminal({
        input: {},
        node: {},
    });
    assert.ok(terminal.mapOver === Terminals.NULL_COLLECTION_TYPE_DESCRIPTION);
});

QUnit.test("constructing with mapOver", function (assert) {
    const terminal = new Terminals.InputTerminal({
        input: {},
        mapOver: new Terminals.CollectionTypeDescription("list"),
    });
    assert.ok(terminal.mapOver.collectionType == "list");
});

QUnit.test("resetMapping", function (assert) {
    const terminal = new Terminals.InputTerminal({
        mapOver: new Terminals.CollectionTypeDescription("list"),
        input: {},
    });
    terminal.node = {
        hasMappedOverInputTerminals: () => true,
        inputTerminals: {},
        outputTerminals: {},
    };
    const changeSpy = sinon.spy();
    terminal.on("change", changeSpy);
    terminal.resetMapping();
    assert.ok(terminal.mapOver === Terminals.NULL_COLLECTION_TYPE_DESCRIPTION);
    assert.ok(changeSpy.called);
});

QUnit.module("terminal mapping logic", {
    newInputTerminal: function (mapOver, input) {
        input = input || {};
        const node = this.newNode();
        if (!("extensions" in input)) {
            input["extensions"] = ["data"];
        }
        const inputEl = $("<div>")[0];
        const inputTerminal = new Terminals.InputTerminal({
            datatypesMapper: testDatatypesMapper,
            element: inputEl,
            input: input,
        });
        inputTerminal.node = node;
        if (mapOver) {
            inputTerminal.setMapOver(new Terminals.CollectionTypeDescription(mapOver));
        }
        return inputTerminal;
    },
    newInputParameterTerminal: function () {
        const node = this.newNode();
        const inputEl = $("<div>")[0];
        const inputTerminal = new Terminals.InputParameterTerminal({
            element: inputEl,
            input: {},
        });
        inputTerminal.node = node;
        return inputTerminal;
    },
    newInputCollectionTerminal: function (input) {
        input = input || {};
        const node = this.newNode();
        if (!("extensions" in input)) {
            input["extensions"] = ["data"];
        }
        const inputEl = $("<div>")[0];
        const inputTerminal = new Terminals.InputCollectionTerminal({
            datatypesMapper: testDatatypesMapper,
            element: inputEl,
            input: input,
            node: node,
        });
        return inputTerminal;
    },
    newOutputTerminal: function (mapOver) {
        const node = this.newNode();
        const outputEl = $("<div>")[0];
        const outputTerminal = new Terminals.OutputTerminal({
            element: outputEl,
            datatypes: ["data"],
            node: {},
        });
        outputTerminal.node = node;
        if (mapOver) {
            outputTerminal.setMapOver(new Terminals.CollectionTypeDescription(mapOver));
        }
        return outputTerminal;
    },
    newOutputCollectionTerminal: function (collectionType) {
        collectionType = collectionType || "list";
        const node = this.newNode();
        const outputEl = $("<div>")[0];
        const outputTerminal = new Terminals.OutputCollectionTerminal({
            element: outputEl,
            datatypes: ["data"],
            collection_type: collectionType,
            node: {},
        });
        outputTerminal.node = node;
        return outputTerminal;
    },
    newNode: function () {
        const nodeEl = $("<div>")[0];
        return new Node({ element: nodeEl });
    },
    _addExistingOutput: function (terminal, output, connected) {
        const self = this;
        const node = terminal.node;
        if (connected) {
            const inputTerminal = self.newInputTerminal();
            new Connector({}, inputTerminal, output);
        }
        this._addTerminalTo(output, node.outputTerminals);
        return output;
    },
    addOutput: function (terminal, connected) {
        const connectedOutput = this.newOutputTerminal();
        return this._addExistingOutput(terminal, connectedOutput, connected);
    },
    addCollectionOutput: function (terminal, connected) {
        const collectionOutput = this.newOutputCollectionTerminal();
        return this._addExistingOutput(terminal, collectionOutput, connected);
    },
    addConnectedOutput: function (terminal) {
        return this.addOutput(terminal, true);
    },
    addConnectedCollectionOutput: function (terminal) {
        const connectedOutput = this.newOutputCollectionTerminal();
        return this._addExistingOutput(terminal, connectedOutput, true);
    },
    addConnectedInput: function (terminal) {
        const self = this;
        const connectedInput = this.newInputTerminal();
        const node = terminal.node;
        const outputTerminal = self.newOutputTerminal();
        new Connector({}, connectedInput, outputTerminal);
        this._addTerminalTo(connectedInput, node.inputTerminals);
        return connectedInput;
    },
    _addTerminalTo: function (terminal, terminals) {
        let name = "other";
        while (name in terminals) {
            name += "_";
        }
        terminals[name] = terminal;
    },
    verifyNotAttachable: function (assert, inputTerminal, output) {
        let outputTerminal;
        if (typeof output == "string") {
            // Just given a collection type... create terminal out of it.
            outputTerminal = this.newOutputTerminal(output);
        } else {
            outputTerminal = output;
        }

        assert.ok(!inputTerminal.attachable(outputTerminal).canAccept);
    },
    verifyAttachable: function (assert, inputTerminal, output) {
        let outputTerminal;
        if (typeof output == "string") {
            // Just given a collection type... create terminal out of it.
            outputTerminal = this.newOutputTerminal(output);
        } else {
            outputTerminal = output;
        }

        assert.ok(
            inputTerminal.attachable(outputTerminal).canAccept,
            "Cannot attach " + outputTerminal + " to " + inputTerminal
        );

        // Go further... make sure datatypes are being enforced
        inputTerminal.datatypes = ["bam"];
        outputTerminal.datatypes = ["txt"];
        assert.ok(!inputTerminal.attachable(outputTerminal).canAccept);
    },
    verifyMappedOver: function (assert, terminal) {
        assert.ok(terminal.mapOver.isCollection);
    },
    verifyNotMappedOver: function (assert, terminal) {
        assert.ok(!terminal.mapOver.isCollection);
    },
    verifyDefaultMapOver: function (assert, terminal) {
        const outputCollectionTerminal = this.newOutputCollectionTerminal("list");
        assert.ok(!terminal.node.mapOver);
        const connector = new Connector({}, outputCollectionTerminal, terminal);
        outputCollectionTerminal.connect(connector);
        assert.ok(terminal.node.mapOver);
        terminal.disconnect(connector);
        assert.ok(!terminal.node.mapOver);
    },
});

QUnit.test("unconstrained input can be mapped over", function (assert) {
    this.inputTerminal1 = this.newInputTerminal();
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("unmapped input can be mapped over if matching connected input terminals map type", function (assert) {
    this.inputTerminal1 = this.newInputTerminal();
    this.addConnectedInput(this.inputTerminal1);
    const connectedInput2 = this.addConnectedInput(this.inputTerminal1);
    connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test(
    "unmapped input cannot be mapped over if not matching connected input terminals map type",
    function (assert) {
        this.inputTerminal1 = this.newInputTerminal();
        const connectedInput = this.addConnectedInput(this.inputTerminal1);
        connectedInput.setMapOver(new Terminals.CollectionTypeDescription("paired"));
        this.verifyNotAttachable(assert, this.inputTerminal1, "list");
    }
);

QUnit.test(
    "unmapped input can be attached to by output collection if matching connected input terminals map type",
    function (assert) {
        this.inputTerminal1 = this.newInputTerminal();
        this.addConnectedInput(this.inputTerminal1);
        const connectedInput2 = this.addConnectedInput(this.inputTerminal1);
        connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list"));
        const outputTerminal = this.newOutputCollectionTerminal("list");
        this.verifyAttachable(assert, this.inputTerminal1, outputTerminal);
    }
);

QUnit.test(
    "unmapped input cannot be attached to by output collection if matching connected input terminals don't match map type",
    function (assert) {
        this.inputTerminal1 = this.newInputTerminal();
        this.addConnectedInput(this.inputTerminal1);
        const connectedInput2 = this.addConnectedInput(this.inputTerminal1);
        connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list"));
        const outputTerminal = this.newOutputCollectionTerminal("paired");
        this.verifyNotAttachable(assert, this.inputTerminal1, outputTerminal);
    }
);

QUnit.test(
    "unmapped input can be attached to by output collection if effective output type (output+mapover) is same as mapped over input",
    function (assert) {
        this.inputTerminal1 = this.newInputTerminal();
        this.addConnectedInput(this.inputTerminal1);
        const connectedInput2 = this.addConnectedInput(this.inputTerminal1);
        connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list:paired"));
        const outputTerminal = this.newOutputCollectionTerminal("paired");
        outputTerminal.setMapOver(new Terminals.CollectionTypeDescription("list"));
        this.verifyAttachable(assert, this.inputTerminal1, outputTerminal);
    }
);

QUnit.test(
    "unmapped input cannot be attached to by output collection if effective output type (output+mapover) is not same as mapped over input (1)",
    function (assert) {
        this.inputTerminal1 = this.newInputTerminal();
        this.addConnectedInput(this.inputTerminal1);
        const connectedInput2 = this.addConnectedInput(this.inputTerminal1);
        connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list:paired"));
        const outputTerminal = this.newOutputCollectionTerminal("list");
        outputTerminal.setMapOver(new Terminals.CollectionTypeDescription("list"));
        this.verifyNotAttachable(assert, this.inputTerminal1, outputTerminal);
    }
);

QUnit.test(
    "unmapped input cannot be attached to by output collection if effective output type (output+mapover) is not same as mapped over input (2)",
    function (assert) {
        this.inputTerminal1 = this.newInputTerminal();
        this.addConnectedInput(this.inputTerminal1);
        const connectedInput2 = this.addConnectedInput(this.inputTerminal1);
        connectedInput2.setMapOver(new Terminals.CollectionTypeDescription("list:paired"));
        const outputTerminal = this.newOutputCollectionTerminal("list");
        outputTerminal.setMapOver(new Terminals.CollectionTypeDescription("paired"));
        this.verifyNotAttachable(assert, this.inputTerminal1, outputTerminal);
    }
);

QUnit.test("unmapped input with unmapped, connected outputs cannot be mapped over", function (assert) {
    // It would invalidate the connections - someday maybe we could try to
    // recursively map over everything down the DAG - it would be expensive
    // to check that though.
    this.inputTerminal1 = this.newInputTerminal();
    this.addConnectedOutput(this.inputTerminal1);
    this.verifyNotAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("unmapped input with connected mapped outputs can be mapped over if matching", function (assert) {
    // It would invalidate the connections - someday maybe we could try to
    // recursively map over everything down the DAG - it would be expensive
    // to check that though.
    this.inputTerminal1 = this.newInputTerminal();
    const connectedOutput = this.addConnectedOutput(this.inputTerminal1);
    connectedOutput.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test(
    "unmapped input with connected mapped outputs cannot be mapped over if mapover not matching",
    function (assert) {
        // It would invalidate the connections - someday maybe we could try to
        // recursively map over everything down the DAG - it would be expensive
        // to check that though.
        this.inputTerminal1 = this.newInputTerminal();
        const connectedOutput = this.addConnectedOutput(this.inputTerminal1);
        connectedOutput.setMapOver(new Terminals.CollectionTypeDescription("paired"));
        this.verifyNotAttachable(assert, this.inputTerminal1, "list");
    }
);

QUnit.test("explicitly constrained input can not be mapped over by incompatible collection type", function (assert) {
    this.inputTerminal1 = this.newInputTerminal();
    this.inputTerminal1.setMapOver(new Terminals.CollectionTypeDescription("paired"));
    this.verifyNotAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("explicitly constrained input can be mapped over by compatible collection type", function (assert) {
    this.inputTerminal1 = this.newInputTerminal();
    this.inputTerminal1.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("unconstrained collection input can be mapped over", function (assert) {
    this.inputTerminal1 = this.newInputCollectionTerminal({ collection_types: ["paired"] });
    this.verifyAttachable(assert, this.inputTerminal1, "list:paired");
});

QUnit.test("unconstrained collection input cannot be mapped over by incompatible type", function (assert) {
    this.inputTerminal1 = this.newInputCollectionTerminal({ collection_types: ["list"] }); // Would need to be paired...
    this.verifyNotAttachable(assert, this.inputTerminal1, "list:paired");
});

QUnit.test("explicitly mapped over collection input can be attached by explicit mapping", function (assert) {
    this.inputTerminal1 = this.newInputCollectionTerminal({ collection_types: ["paired"] });
    this.inputTerminal1.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.verifyAttachable(assert, this.inputTerminal1, "list:paired");
});

QUnit.test("explicitly mapped over collection input can be attached by explicit mapping", function (assert) {
    this.inputTerminal1 = this.newInputCollectionTerminal({ collection_types: ["list:paired"] });
    this.inputTerminal1.setMapOver(new Terminals.CollectionTypeDescription("list"));
    // effectively input is list:list:paired so shouldn't be able to attach
    this.verifyNotAttachable(assert, this.inputTerminal1, "list:paired");
});

QUnit.test("unconnected multiple inputs can be connected to rank 1 collections", function (assert) {
    this.inputTerminal1 = this.newInputTerminal(null, { multiple: true });
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("multiple input attachable by collections", function (assert) {
    this.inputTerminal1 = this.newInputTerminal(null, { multiple: true });
    const connectedInput1 = this.addConnectedInput(this.inputTerminal1);
    this.addConnectedOutput(connectedInput1);
    this.verifyAttachable(assert, this.inputTerminal1, "list");
});

QUnit.test("multiple input attachable by nested collections", function (assert) {
    this.inputTerminal1 = this.newInputTerminal(null, { multiple: true });
    const connectedInput1 = this.addConnectedInput(this.inputTerminal1);
    this.addConnectedOutput(connectedInput1);
    this.verifyAttachable(assert, this.inputTerminal1, "list:list");
});

QUnit.test("Multiple inputs cannot be connected to pairs", function (assert) {
    this.inputTerminal1 = this.newInputTerminal(null, { multiple: true });
    this.verifyNotAttachable(assert, this.inputTerminal1, "list:paired");
});

QUnit.test("resetMappingIfNeeded does nothing if not mapped", function (assert) {
    this.inputTerminal1 = this.newInputTerminal();
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyNotMappedOver(assert, this.inputTerminal1);
});

QUnit.test("resetMappingIfNeeded resets unconstrained input", function (assert) {
    this.inputTerminal1 = this.newInputTerminal("list");
    this.verifyMappedOver(assert, this.inputTerminal1);
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyNotMappedOver(assert, this.inputTerminal1);
});

QUnit.test("resetMappingIfNeeded does not reset if connected output depends on being mapped", function (assert) {
    this.inputTerminal1 = this.newInputTerminal("list");
    const connectedOutput = this.addConnectedOutput(this.inputTerminal1);
    connectedOutput.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyMappedOver(assert, this.inputTerminal1);
});

QUnit.test("resetMappingIfNeeded resets if node outputs are not connected to anything", function (assert) {
    this.inputTerminal1 = this.newInputTerminal("list");
    const output = this.addOutput(this.inputTerminal1);
    output.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyNotMappedOver(assert, this.inputTerminal1);
});

QUnit.test("resetMappingIfNeeded an input resets node outputs if they not connected to anything", function (assert) {
    this.inputTerminal1 = this.newInputTerminal("list");
    const output = this.addOutput(this.inputTerminal1);
    output.setMapOver(new Terminals.CollectionTypeDescription("list"));
    this.inputTerminal1.resetMappingIfNeeded();
    this.verifyNotMappedOver(assert, output);
});

QUnit.test(
    "resetMappingIfNeeded an input resets node collection outputs if they not connected to anything",
    function (assert) {
        this.inputTerminal1 = this.newInputTerminal("list");
        const output = this.addCollectionOutput(this.inputTerminal1);
        output.setMapOver(new Terminals.CollectionTypeDescription("list"));
        this.inputTerminal1.resetMappingIfNeeded();
        this.verifyNotMappedOver(assert, output);
    }
);

QUnit.test("resetMappingIfNeeded resets if not last mapped over input", function (assert) {
    // Idea here is that other nodes are forcing output to still be mapped
    // over so don't need to disconnect output nodes.
    this.inputTerminal1 = this.newInputTerminal("list");
    const connectedInput1 = this.addConnectedInput(this.inputTerminal1);
    connectedInput1.setMapOver(new Terminals.CollectionTypeDescription("list"));
    const connectedOutput = this.addConnectedOutput(this.inputTerminal1);
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

QUnit.test("simple mapping over collection outputs works correctly", function (assert) {
    this.inputTerminal1 = this.newInputTerminal();
    const connectedOutput = this.addConnectedCollectionOutput(this.inputTerminal1);
    this.inputTerminal1.setMapOver(new Terminals.CollectionTypeDescription("list"));

    // Can attach list output of collection type list that is being mapped
    // over another list to a list:list (because this is what it is) but not
    // to a list:list:list.
    const testTerminal2 = this.newInputTerminal("list:list");
    this.verifyAttachable(assert, testTerminal2, connectedOutput);

    const testTerminal1 = this.newInputTerminal("list:list:list");
    this.verifyNotAttachable(assert, testTerminal1, connectedOutput);
});

QUnit.test("node input terminal mapping state over collection outputs works correctly", function (assert) {
    const inputTerminal = this.newInputTerminal();
    this.verifyDefaultMapOver(assert, inputTerminal);
});

QUnit.test("node input parameter terminal mapping state over collection outputs works correctly", function (assert) {
    const inputParameterTerminal = this.newInputParameterTerminal();
    this.verifyDefaultMapOver(assert, inputParameterTerminal);
});
