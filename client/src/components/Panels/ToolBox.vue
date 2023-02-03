<template>
    <div class="unified-panel" aria-labelledby="toolbox-heading">
        <div unselectable="on">
            <div class="unified-panel-header-inner">
                <nav class="d-flex justify-content-between mx-3 my-2">
                    <h2 v-if="!showAdvanced" id="toolbox-heading" v-localize class="m-1 h-sm">Tools</h2>
                    <h2 v-else id="toolbox-heading" v-localize class="m-1 h-sm">Advanced Tool Search</h2>

                    <div class="panel-header-buttons">
                        <b-button-group>
                            <favorites-button v-if="!showAdvanced" :query="query" @onFavorites="onQuery" />
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
                enable-advanced
                :current-panel-view="currentPanelView"
                :placeholder="titleSearchTools"
                :show-advanced.sync="showAdvanced"
                :toolbox="toolbox"
                :query="query"
                @onQuery="onQuery"
                @onResults="onResults" />
            <section v-if="!showAdvanced">
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
            </section>
        </div>
        <div v-if="!showAdvanced" class="unified-panel-body">
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
import { UploadButton } from "components/Upload";
import { useGlobalUploadModal } from "composables/globalUploadModal";
import FavoritesButton from "./Buttons/FavoritesButton";
import PanelViewButton from "./Buttons/PanelViewButton";
import { filterToolSections, filterTools, hasResults, hideToolsSection } from "./utilities";
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
    setup() {
        const { openGlobalUploadModal } = useGlobalUploadModal();
        return { openGlobalUploadModal };
    },
    data() {
        return {
            query: null,
            results: null,
            queryFilter: null,
            queryPending: false,
            showSections: false,
            showAdvanced: false,
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
                return hasResults(this.results)
                    ? filterTools(this.toolbox, this.results)
                    : hideToolsSection(this.toolbox);
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
                this.openGlobalUploadModal();
            } else if (tool.form_style === "regular") {
                evt.preventDefault();
                // encode spaces in tool.id
                const toolId = tool.id;
                const toolVersion = tool.version;
                this.$router.push(`/?tool_id=${encodeURIComponent(toolId)}&version=${toolVersion}`);
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
