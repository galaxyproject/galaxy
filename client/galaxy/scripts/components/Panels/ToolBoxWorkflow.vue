<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-text">Tools</div>
            </div>
        </div>
        <div class="unified-panel-controls">
            <tool-search placeholder="search tools" @onQuery="onQuery" @onResults="onResults" />
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <tool-section
                    v-for="category in moduleSections"
                    :hideName="true"
                    :category="category"
                    toolKey="name"
                    :sectionName="category.name"
                    :queryFilter="query"
                    :disableFilter="true"
                    :key="category.name"
                    @onClick="onInsertModule"
                />
                <tool-section
                    :category="dataManagers"
                    :key="dataManagers.id"
                    :queryFilter="query"
                    :disableFilter="true"
                    @onClick="onInsertTool"
                />
                <div class="toolMenu" id="workflow-tool-menu">
                    <tool-section
                        v-for="category in categories"
                        :category="category"
                        :queryFilter="query"
                        :key="category.id"
                        @onClick="onInsertTool"
                    />
                </div>
                <tool-section
                    :category="workflowSection"
                    :key="workflowSection.name"
                    operationIcon="fa fa-copy"
                    operationTitle="Insert individual steps."
                    :queryFilter="query"
                    :disableFilter="true"
                    @onClick="onInsertWorkflow"
                    @onOperation="onInsertWorkflowSteps"
                />
            </div>
        </div>
    </div>
</template>

<script>
import _l from "utils/localization";
import ToolSection from "./Common/ToolSection";
import ToolSearch from "./Common/ToolSearch";
import { filterToolSections } from "./utilities.js";

export default {
    name: "ToolBox",
    components: {
        ToolSection,
        ToolSearch
    },
    data() {
        return {
            query: null,
            results: null
        };
    },
    props: {
        toolbox: {
            type: Array,
            required: true
        },
        workflowsTitle: {
            type: String,
            default: _l("Workflows")
        },
        workflowSection: {
            type: Object
        },
        workflowGlobals: {
            type: Object
        },
        dataManagers: {
            type: Object
        },
        moduleSections: {
            type: Array
        }
    },
    computed: {
        categories() {
            return filterToolSections(this.toolsLayout, this.results);
        },
        toolsLayout() {
            return this.toolbox.map(section => {
                return {
                    ...section,
                    elems:
                        section.elems &&
                        section.elems.map(el => {
                            el.disabled = !el.is_workflow_compatible;
                            return el;
                        })
                };
            });
        }
    },
    methods: {
        onQuery(query) {
            this.query = query;
        },
        onResults(results) {
            this.results = results;
        },
        onInsertTool(tool, evt) {
            evt.preventDefault();
            this.workflowGlobals.app.add_node_for_tool(tool.id, tool.name);
        },
        onInsertModule(module, evt) {
            evt.preventDefault();
            this.workflowGlobals.app.add_node_for_module(module.name, module.title);
        },
        onInsertWorkflow(workflow, evt) {
            evt.preventDefault();
            this.workflowGlobals.app.add_node_for_subworkflow(workflow.latest_id, workflow.name);
        },
        onInsertWorkflowSteps(workflow) {
            this.workflowGlobals.app.copy_into_workflow(workflow.id, workflow.step_count);
        }
    }
};
</script>
