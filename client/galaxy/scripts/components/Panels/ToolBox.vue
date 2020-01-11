<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons">
                    <favorites-button v-if="isUser" />
                    <upload-button />
                </div>
                <div class="panel-header-text">Tools</div>
            </div>
        </div>
        <div class="unified-panel-controls">
            <tool-search @results="setResults" />
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
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
                    <div class="toolSectionBg"></div>

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
import UploadButton from "./Buttons/UploadButton";
import FavoritesButton from "./Buttons/FavoritesButton";
import { filterToolsLayout, getToolsLayout } from "./utilities.js";
import { getGalaxyInstance } from "app";

export default {
    name: "ToolBox",
    components: {
        UploadButton,
        FavoritesButton,
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
        console.log(this.toolsLayout);
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