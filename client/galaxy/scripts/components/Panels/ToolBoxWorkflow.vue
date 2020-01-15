<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons" />
                <div class="panel-header-text">Tools</div>
            </div>
        </div>
        <div class="unified-panel-controls">
            <tool-search @results="setResults" />
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <tool-section
                    v-for="category in moduleSections"
                    :hideName="true"
                    :category="category"
                    :isFiltered="isFiltered"
                    :key="category.name"
                    @onClick="onInsertModule"
                />
                <tool-section
                    :category="dataManagers"
                    :key="dataManagers.id"
                    :isFiltered="isFiltered"
                    @onClick="onInsertTool"
                />
                <div class="toolMenu">
                    <tool-section
                        v-for="category in categories"
                        :category="category"
                        :isFilterable="true"
                        :isFiltered="isFiltered"
                        :key="category.id"
                        @onClick="onInsertTool"
                    />
                </div>
                <tool-section
                    :category="workflowSection"
                    :key="workflowSection.name"
                    operationIcon="fa fa-copy"
                    operationTitle="Insert individual steps."
                    :isFiltered="isFiltered"
                    @onClick="onInsertWorkflow"
                    @onOperation="onInsertWorkflowSteps"
                />
            </div>
        </div>
    </div>
</template>

<script>
import ToolSection from "./common/ToolSection";
import ToolSearch from "./common/ToolSearch";
import { filterToolSections, getToolSections } from "./utilities.js";

export default {
    name: "ToolBox",
    components: {
        ToolSection,
        ToolSearch
    },
    data() {
        return {
            results: null
        };
    },
    props: {
        toolbox: {
            type: Array
        },
        toolSearch: {
            type: Object
        },
        workflowsTitle: {
            type: String
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
        isFiltered() {
            return !!this.results;
        }
    },
    created() {
        this.toolsLayout = getToolSections(this.toolbox, x => !x.is_workflow_compatible || x.hidden);
    },
    methods: {
        setResults(results) {
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
