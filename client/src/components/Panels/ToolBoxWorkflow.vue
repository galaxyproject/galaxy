<template>
    <div class="unified-panel">
        <div unselectable="on">
            <div class="unified-panel-header-inner">
                <nav class="d-flex justify-content-between mx-3 my-2">
                    <h2 v-localize class="m-1 h-sm">Tools</h2>
                    <div class="panel-header-buttons">
                        <panel-view-button
                            v-if="panelViews && Object.keys(panelViews).length > 1"
                            :panel-views="panelViews"
                            :current-panel-view="currentPanelView"
                            @updatePanelView="updatePanelView" />
                    </div>
                </nav>
            </div>
        </div>
        <div class="unified-panel-controls">
            <tool-search
                :current-panel-view="currentPanelView"
                placeholder="search tools"
                :toolbox="workflowTools"
                :query="query"
                @onQuery="onQuery"
                @onResults="onResults" />
            <div v-if="queryTooShort" class="pb-2">
                <b-badge class="alert-danger w-100">Search string too short!</b-badge>
            </div>
            <div v-else-if="noResults" class="pb-2">
                <b-badge class="alert-danger w-100">No results found!</b-badge>
            </div>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <tool-section
                    v-for="category in moduleSections"
                    :key="category.name"
                    :hide-name="true"
                    :category="category"
                    tool-key="name"
                    :section-name="category.name"
                    :query-filter="query"
                    :disable-filter="true"
                    @onClick="onInsertModule" />
                <tool-section
                    v-if="hasDataManagerSection"
                    :key="dataManagerSection.id"
                    :category="dataManagerSection"
                    :query-filter="query"
                    :disable-filter="true"
                    @onClick="onInsertTool" />
                <tool-section
                    v-for="section in sections"
                    :key="section.id"
                    :category="section"
                    :query-filter="query"
                    @onClick="onInsertTool" />
                <tool-section
                    v-if="hasWorkflowSection"
                    :key="workflowSection.name"
                    :category="workflowSection"
                    section-name="workflows"
                    :sort-items="false"
                    operation-icon="fa fa-files-o"
                    operation-title="Insert individual steps."
                    :query-filter="query"
                    :disable-filter="true"
                    @onClick="onInsertWorkflow"
                    @onOperation="onInsertWorkflowSteps" />
            </div>
        </div>
    </div>
</template>

<script>
import _l from "utils/localization";
import ToolSection from "./Common/ToolSection";
import ToolSearch from "./Common/ToolSearch";
import { filterToolSections, removeDisabledTools } from "./utilities";
import PanelViewButton from "./Buttons/PanelViewButton";

export default {
    name: "ToolBox",
    components: {
        ToolSection,
        ToolSearch,
        PanelViewButton,
    },
    props: {
        toolbox: {
            type: Array,
            required: true,
        },
        panelViews: {
            type: Object,
        },
        currentPanelView: {
            type: String,
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
    data() {
        return {
            query: null,
            results: null,
        };
    },
    computed: {
        queryTooShort() {
            return this.query && this.query.length < 3;
        },
        noResults() {
            return this.query && this.results.length === 0;
        },
        hasWorkflowSection() {
            return this.workflows.length > 0;
        },
        workflowSection() {
            return {
                name: _l("Workflows"),
                elems: this.workflows,
            };
        },
        hasDataManagerSection() {
            return this.dataManagers.length > 0;
        },
        dataManagerSection() {
            return {
                name: _l("Data Managers"),
                elems: this.dataManagers,
            };
        },
        sections() {
            return filterToolSections(this.workflowTools, this.results);
        },
        toolsLayout() {
            return this.toolbox.map((section) => {
                return {
                    ...section,
                    disabled: !section.elems && !section.is_workflow_compatible,
                    elems:
                        section.elems &&
                        section.elems.map((el) => {
                            el.disabled = !el.is_workflow_compatible;
                            return el;
                        }),
                };
            });
        },
        workflowTools() {
            return removeDisabledTools(this.toolsLayout);
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
        updatePanelView(panelView) {
            this.$emit("updatePanelView", panelView);
        },
    },
};
</script>
