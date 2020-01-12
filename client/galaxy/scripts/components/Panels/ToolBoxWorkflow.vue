<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons"/>
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
                    :showName="false"
                    :category="category"
                    :isFiltered="isFiltered"
                    :key="category.id"
                    @onOpen="onOpenModule"
                />
                <tool-section
                    :category="dataManagers"
                    :key="dataManagers.id"
                    :isFiltered="isFiltered"
                    @onOpen="onOpen"
                />
                <div class="toolSectionPad" />
                <div class="toolMenu">
                    <tool-section
                        v-for="category in categories"
                        :category="category"
                        :isFiltered="isFiltered"
                        :key="category.id"
                        @onOpen="onOpen"
                    />
                </div>
                <div class="toolSectionPad" />
                <div class="toolSectionPad" />
                <tool-section
                    :category="workflowSection"
                    :key="workflowSection.name"
                    :isFiltered="isFiltered"
                    @onOpen="onOpenWorkflow"
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
            if (this.results) {
                return true;
            } else {
                return false;
            }
        }
    },
    created() {
        console.log(this.moduleSections);
        this.toolsLayout = getToolSections(this.toolbox, x => !x.is_workflow_compatible || x.hidden);

    },
    methods: {
        setResults(results) {
            this.results = results;
        },
        onOpen(e, tool) {
            e.preventDefault();
            this.workflowGlobals.app.add_node_for_tool( tool.id, tool.name );
        },
        onOpenModule(e, module) {
            e.preventDefault();
            this.workflowGlobals.app.add_node_for_module( module.name, module.title );
        },
        onOpenWorkflow(e, workflow) {
            e.preventDefault();
            this.workflowGlobals.app.add_node_for_subworkflow( workflow.id, workflow.name );
        }
    }
};
</script>