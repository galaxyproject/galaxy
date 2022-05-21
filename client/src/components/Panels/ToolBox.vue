<template>
    <div class="unified-panel">
        <div unselectable="on">
            <div class="unified-panel-header-inner">
                <nav class="d-flex justify-content-between mx-3 my-2">
                    <h4 v-localize class="m-1">Tools</h4>
                    <div class="panel-header-buttons">
                        <b-button-group>
                            <favorites-button v-if="isUser" :query="query" @onFavorites="onQuery" />
                            <panel-view-button
                                v-if="panelViews && Object.keys(panelViews).length > 1"
                                :panel-views="panelViews"
                                :current-panel-view="currentPanelView"
                                @updatePanelView="updatePanelView" />
                        </b-button-group>
                    </div>
                </nav>
            </div>
        </div>
        <div class="unified-panel-controls">
            <tool-search
                :current-panel-view="currentPanelView"
                :placeholder="titleSearchTools"
                :query="query"
                @onQuery="onQuery"
                @onResults="onResults" />
            <upload-button />
            <div v-if="hasResults" class="pb-2">
                <b-button size="sm" class="w-100" @click="onToggle">
                    <span :class="buttonIcon" />
                    <span class="mr-1">{{ buttonText }}</span>
                </b-button>
            </div>
            <div v-else-if="queryTooShort" class="pb-2">
                <b-badge class="alert-danger w-100">Search string too short!</b-badge>
            </div>
            <div v-else-if="queryFinished" class="pb-2">
                <b-badge class="alert-danger w-100">No results found!</b-badge>
            </div>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <div class="toolMenu">
                    <tool-section
                        v-for="(section, key) in sections"
                        :key="key"
                        :category="section"
                        :query-filter="queryFilter"
                        @onClick="onOpen" />
                </div>
                <tool-section :category="{ text: workflowTitle }" />
                <div id="internal-workflows" class="toolSectionBody">
                    <div class="toolSectionBg" />
                    <div v-for="wf in workflows" :key="wf.id" class="toolTitle">
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
        onQuery(q) {
            this.query = q;
            this.queryPending = true;
        },
        onResults(results) {
            this.results = results;
            this.queryFilter = this.hasResults ? this.query : null;
            this.setButtonText();
            this.queryPending = false;
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
