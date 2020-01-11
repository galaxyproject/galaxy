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
                <div v-for="moduleSection in moduleSections" :key="moduleSection.name">
                    <div class="toolSectionTitle" role="button">
                        <a>{{ moduleSection.title }}</a>
                    </div>
                    <div class="toolSectionBody">
                        <div class="toolSectionBg">
                            <div class="toolTitle" v-for="module in moduleSection.modules" :key="module.name">
                                <a role="button" href="javascript:void(0)">
                                    {{ module.description }}
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
                <tool-section
                    :category="dataManagers"
                    :key="dataManagers.name"
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
                <div class="toolSectionTitle" id="title_XXinternalXXworkflow">
                    <a>{{ workflowsTitle }}</a>
                </div>
                <div id="internal-workflows" class="toolSectionBody">
                    <div class="toolSectionBg"/>
                    <div class="toolTitle" v-for="workflow in workflows" :key="workflow.id">
                        <a :href="workflow.href">
                            {{ workflow.title }}
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import ToolSection from "./common/ToolSection";
import ToolSearch from "./common/ToolSearch";
import { filterToolsLayout, getToolsLayout } from "./utilities.js";
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
        tools: {
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
            type: Array
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
            return filterToolsLayout(this.toolsLayout, this.results);
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
        this.toolsLayout = getToolsLayout();
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