<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons">
                </div>
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
                    :category="category"
                    :isFiltered="isFiltered"
                    :key="category.id"
                    @onOpen="onOpen"
                />
                <tool-section
                    :category="dataManagers"
                    :key="dataManagers.name"
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
                    :category="workflows"
                    :key="workflows.name"
                    :isFiltered="isFiltered"
                    @onOpen="onOpen"
                />
            </div>
        </div>
    </div>
</template>

<script>
import ToolSection from "./common/ToolSection";
import ToolSearch from "./common/ToolSearch";
import { filterToolSections, getToolSections } from "./utilities.js";
import { getGalaxyInstance } from "app";

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
        toolSections: {
            type: Array
        },
        toolSearch: {
            type: Object
        },
        workflowsTitle: {
            type: String
        },
        workflows: {
            type: Array
        },
        dataManagers: {
            type: Object
        },
        moduleSections: {
            type: Array
        },
        isUser: {
            type: Boolean,
            default: false
        }
    },
    computed: {
        categories() {
            return filterToolSections(this.toolSections, this.results);
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
        const Galaxy = getGalaxyInstance();
        this.toolsLayout = getToolSections(Galaxy.config);
    },
    methods: {
        setResults(results) {
            this.results = results;
        },
        onOpen(e, tool) {
            const Galaxy = getGalaxyInstance();
            if (tool.id === "upload1") {
                e.preventDefault();
                Galaxy.upload.show();
            } else if (tool.form_style === "regular") {
                e.preventDefault();
                Galaxy.router.push("/", {
                    tool_id: tool.id,
                    version: tool.version
                });
            }
        }
    }
};
</script>