<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-buttons">
                    <favorites-button :query="query" @onFavorites="onFavorites" v-if="isUser" />
                    <panel-view-button
                        :panel-views="panelViews"
                        :current-panel-view="currentPanelView"
                        @updatePanelView="updatePanelView"
                        v-if="panelViews && Object.keys(panelViews).length > 1" />
                </div>
                <div class="panel-header-text" v-localize>Tools</div>
            </div>
        </div>
        <div class="unified-panel-controls">
            <tool-search
                :current-panel-view="currentPanelView"
                :query="query"
                :placeholder="titleSearchTools"
                @onQuery="onQuery"
                @onResults="onResults" />
            <upload-button />
            <div class="py-2" v-if="hasResults">
                <b-button @click="onToggle" size="sm" class="w-100">
                    <span :class="buttonIcon" />
                    <span class="mr-1">{{ buttonText }}</span>
                </b-button>
            </div>
            <div class="py-2" v-else-if="queryTooShort">
                <b-badge class="alert-danger w-100">Search string too short!</b-badge>
            </div>
            <div class="py-2" v-else-if="queryFinished">
                <b-badge class="alert-danger w-100">No results found!</b-badge>
            </div>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <div class="toolMenu">
                    <tool-section
                        v-for="(section, key) in sections"
                        :category="section"
                        :query-filter="queryFilter"
                        :key="key"
                        @onClick="onOpen" />
                </div>
                <tool-section :category="{ text: workflowTitle }" />
                <div id="internal-workflows" class="toolSectionBody">
                    <div class="toolSectionBg" />
                    <div class="toolTitle" v-for="wf in workflows" :key="wf.id">
                        <a class="title-link" :href="wf.href">{{ wf.title }}</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import ToolSection from "./Common/ToolSection";
import ToolSearch from "./Common/ToolSearch";
import { UploadButton, openGlobalUploadModal } from "components/Upload";
import FavoritesButton from "./Buttons/FavoritesButton";
import PanelViewButton from "./Buttons/PanelViewButton";
import { filterToolSections, filterTools } from "./utilities";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import _l from "utils/localization";

export default {
    components: {
        UploadButton,
        FavoritesButton,
        PanelViewButton,
        ToolSection,
        ToolSearch,
    },
    data() {
        return {
            query: null,
            results: null,
            queryFilter: null,
            queryPending: false,
            showSections: false,
            buttonText: "",
            buttonIcon: "",
            titleSearchTools: _l("search tools"),
        };
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
        storedWorkflowMenuEntries: {
            type: Array,
            required: true,
        },
        workflowTitle: {
            type: String,
            default: _l("Workflows"),
        },
    },
    computed: {
        queryTooShort() {
            return this.query && this.query.length < 3;
        },
        queryFinished() {
            return this.query && this.queryPending != true;
        },
        sections() {
            if (this.showSections) {
                return filterToolSections(this.toolbox, this.results);
            } else {
                return filterTools(this.toolbox, this.results);
            }
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
                ...this.storedWorkflowMenuEntries.map((menuEntry) => {
                    return {
                        id: menuEntry.id,
                        title: menuEntry.name,
                        href: `${getAppRoot()}workflows/run?id=${menuEntry.id}`,
                    };
                }),
            ];
        },
        hasResults() {
            return this.results && this.results.length > 0;
        },
    },
    methods: {
        onQuery(query) {
            this.query = query;
            this.queryPending = true;
        },
        onResults(results) {
            this.results = results;
            this.queryFilter = this.hasResults ? this.query : null;
            this.setButtonText();
            this.queryPending = false;
        },
        onFavorites(term) {
            this.query = term;
        },
        onOpen(tool, evt) {
            if (tool.id === "upload1") {
                evt.preventDefault();
                openGlobalUploadModal();
            } else if (tool.form_style === "regular") {
                evt.preventDefault();
                const Galaxy = getGalaxyInstance();
                // encode spaces in tool.id
                Galaxy.router.push("/", {
                    tool_id: tool.id.replace(/ /g, "%20"),
                    version: tool.version,
                });
            }
        },
        onToggle() {
            this.showSections = !this.showSections;
            this.setButtonText();
        },
        setButtonText() {
            this.buttonText = this.showSections ? _l("Hide Sections") : _l("Show Sections");
            this.buttonIcon = this.showSections ? "fa fa-eye-slash" : "fa fa-eye";
        },
        updatePanelView(panelView) {
            this.$emit("updatePanelView", panelView);
        },
    },
};
</script>
