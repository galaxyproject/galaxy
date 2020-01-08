<template>
    <div class="unified-panel-wrapper">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons">
                    <favorites-button v-if="isUser"></favorites-button>
                    <upload-button></upload-button>
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
                    ></tool-section>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionPad"></div>

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
import ToolSection from "./ToolSection";
import ToolSearch from "./ToolSearch";
import UploadButton from "./Buttons/UploadButton";
import FavoritesButton from "./Buttons/FavoritesButton";
import { toolsLayout } from "./utilities.js";
import _ from "underscore";

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
        layout: {
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
            return toolsLayout(this.layout, this.results)
        },
        isFiltered() {
            if (this.results) {
                return true;
            } else {
                return false;
            }
        }
    },
    methods: {
        setResults(results) {
            this.results = results;
        }
    }
};
</script>

<style scoped>
.unified-panel-wrapper {
    display: flex;
    flex-flow: column;
    height: 100%;
    overflow: auto;
}
</style>
