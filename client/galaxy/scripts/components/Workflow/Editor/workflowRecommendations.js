import _ from "underscore";
import $ from "jquery";
import Vue from "vue";
import WorkflowToolRecommendations from "components/Workflow/Editor/WorkflowRecommendationsVue";

function getToolId(toolId) {
    if (toolId !== undefined && toolId !== null && toolId.indexOf("/") > -1) {
        let toolIdSlash = toolId.split("/");
        toolId = toolIdSlash[toolIdSlash.length - 2];
    }
    return toolId;
}

function getWorkflowPath(wf_steps, current_node_id, current_node_name) {
        let steps = {};
        let step_names = {};
        for (let stp_idx in wf_steps.steps) {
            let step = wf_steps.steps[stp_idx];
            let input_connections = step.input_connections;
            step_names[step.id] = getToolId(step.content_id);
            for (let ic_idx in input_connections) {
                let ic = input_connections[ic_idx];
                if(ic !== null && ic !== undefined) {
                    let prev_conn = [];
                    for (let conn of ic) {
                        prev_conn.push(conn.id.toString());
                    }
                    steps[step.id.toString()] = prev_conn;
                }
            }
        }
        // recursive call to determine path
        function readPaths(node_id, ph) {
            for (let st in steps) {
                if (parseInt(st) === parseInt(node_id)) {
                    let parent_id = parseInt(steps[st][0]);
                    if (parent_id !== undefined && parent_id !== null) {
                        ph.push(parent_id);
                        if (steps[parent_id] !== undefined && steps[parent_id] !== null) {
                            readPaths(parent_id, ph);
                        }
                    }
                }
            }
            return ph;
        }
        let ph = [];
        let step_names_list = [];
        ph.push(current_node_id);
        ph = readPaths(current_node_id, ph);
        for (let s_idx of ph) {
            let s_name = step_names[s_idx.toString()];
            if (s_name !== undefined && s_name !== null) {
                step_names_list.push(s_name);
            }
        }
        return step_names_list.join(",");
}

export function getToolRecommendations(props) {
        const workflowSimple = props.node.app.to_simple();
        const node = props.node;
        const toolId = getToolId(node.content_id);
        const toolSequence = getWorkflowPath(workflowSimple, node.id, toolId);
        
        // show tool recommendations
        const ToolRecommendationInstance = Vue.extend(WorkflowToolRecommendations);
        const vm = document.createElement("div");
        $("body").append(vm);
        const instance = new ToolRecommendationInstance({
             propsData: {
                 workflowManager: props,
                 toolSequence: toolSequence
             },
        });
        instance.$mount(vm);
        
        // remove ui-modal if present
        /*let $modal = $(".modal-tool-recommendation");
        if ($modal.length > 0) {
            $modal.remove();
        }
        // create new modal
        let modal = new Modal.View({
            title: "Recommended tools",
            body: "<div> Loading tools ... </div>",
            height: "230",
            width: "250",
            closing_events: true,
            title_separator: true        
        });
        modal.$el.addClass("modal-tool-recommendation");
        modal.$el.find(".modal-header").attr("title", "The recommended tools are shown in the decreasing order of their scores predicted using machine learning analysis on workflows. A tool with a higher score (closer to 100%) may fit better as the following tool than a tool with a lower score. Please click on one of the following/recommended tools to have it on the workflow editor.");
        modal.$el.find(".modal-body").css("overflow", "auto");
        modal.show();
        axios
            .post(`${getAppRoot()}api/workflows/get_tool_predictions`, {
                tool_sequence: toolSequence,
            })
            .then((data) => {
                let predTemplate = "<div>";
                let predictedData = data.predicted_data;
                let outputDatatypes = predictedData["o_extensions"];
                let predictedDataChildren = predictedData.children;
                let noRecommendationsMessage = "No tool recommendations";
                if (predictedDataChildren.length > 0) {
                    let compatibleTools = {};
                    // filter results based on datatype compatibility
                    for (const [index, name_obj] of predictedDataChildren.entries()) {
                        let inputDatatypes = name_obj["i_extensions"];
                        for (const out_t of outputDatatypes.entries()) {
                            for(const in_t of inputDatatypes.entries()) {
                                if ((propsData.node.app.isSubType(out_t[1], in_t[1]) === true) ||
                                     out_t[1] === "input" ||
                                     out_t[1] === "_sniff_" ||
                                     out_t[1] === "input_collection") {
                                    compatibleTools[name_obj["tool_id"]] = name_obj["name"];
                                    break
                                }
                            }
                        }
                    }
                    predTemplate += "<div>";
                    if (Object.keys(compatibleTools).length > 0 && predictedData["is_deprecated"] === false) {
                        for (let id in compatibleTools) {
                            predTemplate += "<i class='fa mr-1 fa-wrench'></i><a href='#' title='Click to open the tool' class='pred-tool panel-header-button' id=" + "'" + id + "'" + ">" + compatibleTools[id];
                            predTemplate += "</a></br>";
                        }
                    }
                    else if (predictedData["is_deprecated"] === true) {
                        predTemplate += predictedData["message"];
                    }
                    else {
                        predTemplate += noRecommendationsMessage;
                    }
                    predTemplate += "</div>";
                }
                else {
                    predTemplate += noRecommendationsMessage; 
                }
                predTemplate += "</div>";
                modal.$body.html(predTemplate);
                $(".pred-tool").click(e => {
                    workflow_globals.app.add_node_for_tool(e.target.id, e.target.id);
                    modal.hide();
                });
            });*/
    }
