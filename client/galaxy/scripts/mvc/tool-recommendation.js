import Backbone from "backbone";
import Utils from "utils/utils";
import * as d3 from "d3";
import { getAppRoot } from "onload/loadConfig";
import $ from "jquery";


var ToolRecommendationView = Backbone.View.extend({
    el: "#tool-recommendation-view",

    initialize: function(options) {
        let toolId = options.toolId || "";
        const self = this;
        if (toolId.indexOf("/") > 0) {
            const toolIdSlash = toolId.split("/");
            toolId = toolIdSlash[toolIdSlash.length - 2];
        }
        Utils.request({
            type: "POST",
            url: `${getAppRoot()}api/workflows/get_tool_predictions`,
            data: {"tool_sequence": toolId},
            success: data => {
                // get datatypes mapping
                const datatypes_mapping = JSON.parse(
                    $.ajax({
                        url: `${getAppRoot()}api/datatypes/mapping`,
                        async: false
                    }).responseText
                ),
                extToType = datatypes_mapping.ext_to_class_name,
                typeToType = datatypes_mapping.class_to_classes,
                predData = data.predicted_data;
                if (data !== null && predData.children.length > 0) {
                    const filteredData = {},
                        compatibleTools = {},
                        filteredChildren = [],
                        outputDatatypes = predData["o_extensions"],
                        children = predData.children;
                    for (const nameObj of children.entries()) {
                        const inputDatatypes = nameObj[1]["i_extensions"];
                        for (const out_t of outputDatatypes.entries()) {
                            for(const in_t of inputDatatypes.entries()) {
                                const child = extToType[out_t[1]],
                                    parent = extToType[in_t[1]];
                                if (((typeToType[child] && parent in typeToType[child]) === true) ||
                                     out_t[1] === "input" ||
                                     out_t[1] === "_sniff_" ||
                                     out_t[1] === "input_collection") {
                                    compatibleTools[nameObj[1]["tool_id"]] = nameObj[1]["name"];
                                    break
                                }
                            }
                        }
                    }
                    for (const id in compatibleTools) {
                        for (const nameObj of children.entries()) {
                            if (nameObj[1]["tool_id"] === id) {
                                filteredChildren.push(nameObj[1]);
                                break
                            }
                        }
                    }
                    filteredData["o_extensions"] = predData["o_extensions"];
                    filteredData["name"] = predData["name"];
                    filteredData["children"] = filteredChildren;
                    if (filteredChildren.length > 0 && predData["is_deprecated"] === false) {
                        self.$el.append("<div class='infomessagelarge'>You have used " + filteredData.name + " tool. For further analysis, you could try using the following/recommended tools. The recommended tools are shown in the decreasing order of their scores predicted using machine learning analysis on workflows. A tool with a higher score (closer to 100%) may fit better as the following tool than a tool with a lower score. Please click on one of the following/recommended tools to open its definition. </div>");
                        self.render_tree(filteredData);
                    }
                    else if(predData["is_deprecated"] === true) {
                        self.$el.append("<div class='warningmessagelarge'>You have used " + predData.name + " tool. " + predData["message"] + ". </div>");
                    }
                }
            }
        });
    },

    render_tree: function(predicted_data) {
        const margin = {top: 20, right: 30, bottom: 20, left: 250},
            width = 900 - margin.right - margin.left,
            height = 300 - margin.top - margin.bottom,
            duration = 750;
        const tree = d3.layout.tree()
            .size([height, width]);
        const diagonal = d3.svg.diagonal()
            .projection(d => { return [d.y, d.x]; })
        const svg = d3.select("#tool-recommendation-view").append("svg")
            .attr("width", width + margin.right + margin.left)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
        let i = 0,
            root = null;
        function update(source) {
            // Compute the new tree layout.
            const nodes = tree.nodes(root).reverse(),
                links = tree.links(nodes);
            // Normalize for fixed-depth.
            nodes.forEach(d => { d.y = d.depth * 180; });
            // Update the nodes…
            const node = svg.selectAll("g.node")
                .data(nodes, d => { return d.id || (d.id = ++i); });
            // Enter any new nodes at the parent's previous position.
            const nodeEnter = node.enter().append("g")
                .attr("class", "node")
                .attr("transform", d => { return "translate(" + source.y0 + "," + source.x0 + ")"; })
                .on("click", click);
            nodeEnter.append("circle")
                .attr("r", 1e-6)
                .style("fill", d => { return d._children ? "lightsteelblue" : "#fff"; });
            nodeEnter.append("text")
                .attr("x", d => { return d.children || d._children ? -10 : 10; })
                .attr("dy", ".35em")
                .attr("text-anchor", d => { return d.children || d._children ? "end" : "start"; })
                .text(d => { return d.name; })
                .style("fill-opacity", 1e-6);
            nodeEnter.append("title")
                .text(d => { return d.children || d._children ? "Click to collapse" : "Click to open tool definition"; })
            // Transition nodes to their new position.
            const nodeUpdate = node.transition()
                .duration(duration)
                .attr("transform", d => { return "translate(" + d.y + "," + d.x + ")"; });
            nodeUpdate.select("circle")
                .attr("r", 4.5)
                .style("fill", d => { return d._children ? "lightsteelblue" : "#fff"; });
            nodeUpdate.select("text")
                .style("fill-opacity", 1);
            // Transition exiting nodes to the parent's new position.
            const nodeExit = node.exit().transition()
                .duration(duration)
                .attr("transform", d => { return "translate(" + source.y + "," + source.x + ")"; })
                .remove();
            nodeExit.select("circle")
                .attr("r", 1e-6);
            nodeExit.select("text")
                .style("fill-opacity", 1e-6);
            // Update the links…
            const link = svg.selectAll("path.link")
                .data(links, d => { return d.target.id; });
            // Enter any new links at the parent's previous position.
            link.enter().insert("path", "g")
                .attr("class", "link")
                .attr("d", d => {
                    const o = {x: source.x0, y: source.y0};
                    return diagonal({source: o, target: o});
                });
            // Transition links to their new position.
            link.transition()
                .duration(duration)
                .attr("d", diagonal);
            // Transition exiting nodes to the parent's new position.
            link.exit().transition()
                .duration(duration)
                .attr("d", d => {
                    const o = {x: source.x, y: source.y};
                    return diagonal({source: o, target: o});
                })
                .remove();
            // Stash the old positions for transition.
            nodes.forEach(d => {
                d.x0 = d.x;
                d.y0 = d.y;
            });
        }
        // Toggle children on click.
        function click(d) {
            if (d.children) {
                d._children = d.children;
                d.children = null;
            } else {
                d.children = d._children;
                d._children = null;
            }
            update(d);
            if (d.tool_id !== undefined && d.tool_id !== "undefined" && d.tool_id !== null && d.tool_id !== "") {
                document.location.href = `${getAppRoot()}` + 'tool_runner?tool_id=' + d.tool_id;
            }
        }
        function collapse(d) {
            if (d.children) {
                d._children = d.children;
                d._children.forEach(collapse);
                d.children = null;
            }
        }
        d3.select(self.frameElement).style("height", "400px");
        root = predicted_data;
        root.x0 = height / 2;
        root.y0 = 0;
        root.children.forEach(collapse);
        update(root);
    }
});

export default {
    ToolRecommendationView: ToolRecommendationView
};
