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
                    :hide-name="true"
                    :category="category"
                    tool-key="name"
                    :section-name="category.name"
                    :query-filter="query"
                    :disable-filter="true"
                    :key="category.name"
                    @onClick="onInsertModule"
                />
                <tool-section
                    :category="dataManagerSection"
                    :key="dataManagerSection.id"
                    :query-filter="query"
                    :disable-filter="true"
                    @onClick="onInsertTool"
                />
                <div class="toolMenu" id="workflow-tool-menu">
                    <tool-section
                        v-for="category in categories"
                        :category="category"
                        :query-filter="query"
                        :key="category.id"
                        @onClick="onInsertTool"
                    />
                </div>
                <tool-section
                    :category="workflowSection"
                    :key="workflowSection.name"
                    operation-icon="fa fa-files-o"
                    operation-title="Insert individual steps."
                    :query-filter="query"
                    :disable-filter="true"
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
import { filterToolSections } from "./utilities";

export default {
    name: "ToolBox",
    components: {
        ToolSection,
        ToolSearch,
    },
    data() {
        return {
            query: null,
            results: null,
        };
    },
    props: {
        toolbox: {
            type: Array,
            required: true,
        },
        workflows: {
            type: Array,
            required: true,
        },
        dataManagers: {
            type: Array,
            required: true,
        },
        moduleSections: {
            type: Array,
            required: true,
        },
    },
    computed: {
        workflowSection() {
            return {
                name: _l("Workflows"),
                elems: this.workflows,
            };
        },
        dataManagerSection() {
            return {
                name: _l("Data Managers"),
                elems: this.dataManagers,
            };
        },
        categories() {
            return filterToolSections(this.toolsLayout, this.results);
        },
        toolsLayout() {
            return this.toolbox.map((section) => {
                return {
                    ...section,
                    elems:
                        section.elems &&
                        section.elems.map((el) => {
                            el.disabled = !el.is_workflow_compatible;
                            return el;
                        }),
                };
            });
        },
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
            this.$emit("onInsertTool", tool.id, tool.name);
        },
        onInsertModule(module, evt) {
            evt.preventDefault();
            this.$emit("onInsertModule", module.name, module.title);
        },
        onInsertWorkflow(workflow, evt) {
            evt.preventDefault();
            this.$emit("onInsertWorkflow", workflow.latest_id, workflow.name);
        },
        onInsertWorkflowSteps(workflow) {
            this.$emit("onInsertWorkflowSteps", workflow.id, workflow.step_count);
        },
    },
};
</script>
