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
                        :isFilterable="true"
                        :isFiltered="isFiltered"
                        :key="category.id"
                        @onClick="onOpen"
                    />
                </div>
                <div class="toolSectionTitle" id="title_XXinternalXXworkflow">
                    <a>{{ workflowsTitle }}</a>
                </div>
                <div id="internal-workflows" class="toolSectionBody">
                    <div class="toolSectionBg" />
                    <div class="toolTitle" v-for="workflow in this.workflows" :key="workflow.id">
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
import { filterToolSections } from "./utilities.js";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import _l from "utils/localization";

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
            results: null,
            workflow: null
        };
    },
    props: {
        toolbox: {
            type: Array,
            required: true
        },
        stored_workflow_menu_entries: {
            type: Array,
            required: true
        },
        workflowsTitle: {
            type: String,
            default: _l("Workflows")
        }
    },
    computed: {
        categories() {
            return filterToolSections(this.toolbox, this.results);
        },
        isFiltered() {
            return !!this.results;
        },
        isUser() {
            const Galaxy = getGalaxyInstance();
            return !!(Galaxy.user && Galaxy.user.id);
        }
    },
    created() {
        this.workflows = this.getWorkflows(this.stored_workflow_menu_entries);
    },
    methods: {
        getWorkflows(stored_workflow_menu_entries) {
            const storedWorkflowMenuEntries = stored_workflow_menu_entries || [];
            return [
                {
                    title: _l("All workflows"),
                    href: `${getAppRoot()}workflows/list`,
                    id: "list"
                },
                ...storedWorkflowMenuEntries.map(menuEntry => {
                    return {
                        title: menuEntry.stored_workflow.name,
                        href: `${getAppRoot()}workflows/run?id=${menuEntry.encoded_stored_workflow_id}`,
                        id: menuEntry.encoded_stored_workflow_id
                    };
                })
            ];
        },
        setResults(results) {
            this.results = results;
        },
        onOpen(tool, evt) {
            const Galaxy = getGalaxyInstance();
            if (tool.id === "upload1") {
                evt.preventDefault();
                Galaxy.upload.show();
            } else if (tool.form_style === "regular") {
                evt.preventDefault();
                Galaxy.router.push("/", {
                    tool_id: tool.id,
                    version: tool.version
                });
            }
        }
    }
};
</script>
