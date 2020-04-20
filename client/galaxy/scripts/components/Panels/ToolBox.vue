<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons">
                    <favorites-button @onFavorites="onFavorites" v-if="isUser" />
                    <upload-button />
                </div>
                <div class="panel-header-text">Tools</div>
            </div>
        </div>
        <div class="unified-panel-controls">
            <tool-search :query="query" placeholder="search tools" @onQuery="onQuery" @onResults="onResults" />
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <div class="toolMenu">
                    <tool-section
                        v-for="category in categories"
                        :category="category"
                        :query-filter="query"
                        :key="category.id"
                        @onClick="onOpen"
                    />
                </div>
                <div class="toolSectionTitle" id="title_XXinternalXXworkflow">
                    <a>{{ workflowTitle }}</a>
                </div>
                <div id="internal-workflows" class="toolSectionBody">
                    <div class="toolSectionBg" />
                    <div class="toolTitle" v-for="wf in this.workflows" :key="wf.id">
                        <a :href="wf.href">
                            {{ wf.title }}
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import ToolSection from "./Common/ToolSection";
import ToolSearch from "./Common/ToolSearch";
import UploadButton from "./Buttons/UploadButton";
import FavoritesButton from "./Buttons/FavoritesButton";
import { filterToolSections } from "./utilities";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import _l from "utils/localization";

export default {
    name: "ToolBox",
    components: {
        UploadButton,
        FavoritesButton,
        ToolSection,
        ToolSearch,
    },
    data() {
        return {
            query: null,
            results: null,
            workflow: null,
        };
    },
    props: {
        toolbox: {
            type: Array,
            required: true,
        },
        stored_workflow_menu_entries: {
            type: Array,
            required: true,
        },
        workflowTitle: {
            type: String,
            default: _l("Workflows"),
        },
    },
    computed: {
        categories() {
            return filterToolSections(this.toolbox, this.results);
        },
        isUser() {
            const Galaxy = getGalaxyInstance();
            return !!(Galaxy.user && Galaxy.user.id);
        },
        workflows() {
            return [
                {
                    title: _l("All workflows"),
                    href: `${getAppRoot()}workflows/list`,
                    id: "list",
                },
                ...this.stored_workflow_menu_entries.map((menuEntry) => {
                    return {
                        id: menuEntry.id,
                        title: menuEntry.name,
                        href: `${getAppRoot()}workflows/run?id=${menuEntry.id}`,
                    };
                }),
            ];
        },
    },
    methods: {
        onQuery(query) {
            this.query = query;
        },
        onResults(results) {
            this.results = results;
        },
        onFavorites(term) {
            this.query = term;
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
                    version: tool.version,
                });
            }
        },
    },
};
</script>
