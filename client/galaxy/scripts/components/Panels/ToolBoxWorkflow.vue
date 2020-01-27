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
                    :category="dataManagers"
                    :key="dataManagers.id"
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
                    operation-icon="fa fa-copy"
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
import ToolSection from "./Common/ToolSection";
import ToolSearch from "./Common/ToolSearch";
import { filterToolSections } from "./utilities";

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
