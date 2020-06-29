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
            <div class="toolset" v-if="toolsetEnabled">
                <!--Only Display if toolsets are configured-->
                <select
                    placeholder="Select a Toolset"
                    v-model="selected"
                    :options="toolsets"
                >
                    <option v-for="toolset in toolsets" :key="toolset" @click="getToolsetToolIds(toolset)">
                        {{ toolset }}
                    </option>
                </select>

                <!-- <multiselect
                    placeholder="Select a Toolset"
                    v-model="selected"
                    :options="toolsets"
                    :click="getToolsetToolIds"
                >
                </multiselect> -->

                <span><input type="checkbox" id="checkbox" v-model="detailedView" @change="onPanelResize">
                    Show detailed tools view
                </span>

                <tools-view v-if="showDetailedView" :toolset="getToolsetTools" tool-open="_self" />
            </div>

            <div class="toolsearch">
                <tool-search v-if="!showDetailedView" :query="query" placeholder="search tools" @onQuery="onQuery" @onResults="onResults" />

                <div class="py-2" v-if="hasResults">
                    <b-button @click="onToggle">{{ buttonText }}</b-button>
                </div>
                <div class="py-2" v-else-if="query">
                    <span v-if="query.length < 3" class="font-weight-bold">***Search string too short***</span>
                    <span v-else class="font-weight-bold">***No Results Found***</span>
                </div>
            </div>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer" v-if="!showDetailedView">
                <div class="toolMenu">
                    <tool-section
                        v-for="section in sections"
                        :category="section"
                        :query-filter="queryFilter"
                        :key="section.id"
                        @onClick="onOpen"
                    />
                </div>
                <div class="toolPanelLabel" id="title_XXinternalXXworkflow">
                    <a>{{ workflowTitle }}</a>
                </div>
                <div id="internal-workflows" class="toolSectionBody">
                    <div class="toolSectionBg" />
                    <div class="toolTitle" v-for="wf in workflows" :key="wf.id">
                        <a :href="wf.href">{{ wf.title }}</a>
                    </div>
                </div>
            </div>
        </div>

        <!--<div class="vld-parent">

            <li v-for="tool in searchTools" :key="tool.id">
                {{ tool.name }}
                <favorites-button @onFavorites="onAddFavorite" v-if="isUser" />
            </li>
        </div>-->
    </div>
</template>

<script>
//import Multiselect from "vue-multiselect";
import ToolSection from "./Common/ToolSection";
import ToolSearch from "./Common/ToolSearch";
import UploadButton from "./Buttons/UploadButton";
import FavoritesButton from "./Buttons/FavoritesButton";
import ToolsView from "components/ToolsView/ToolsView"
import { filterToolSections, filterTools, filterToolsets, resizePanel } from "./utilities";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import svc from "./service";
import _l from "utils/localization";

export default {
    name: "ToolBox",
    components: {
        //Multiselect,
        UploadButton,
        FavoritesButton,
        ToolSection,
        ToolSearch,
        ToolsView,
    },
    data() {
        return {
            query: null,
            results: null,
            queryFilter: null,
            showSections: false,
            buttonText: "",
            mainToolbox: "Main Toolbox",
            selected: "Main Toolbox",
            toolsets: ["Main Toolbox"],
            toolsetIds: [],
            savedWidth: null,
            toolsetTools: [],
            detailedView: false,
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
        sections() {
            // Searching through toolset
            if (this.selected != this.mainToolbox && this.results) {
                console.log("SEARCH TOOLSET");
                return filterToolsets(this.toolbox, this.toolsetIds, this.results);
                //account for this.showSections here too
            }

            var searchList = this.toolsetIds ? this.toolsetIds : this.results;

            return this.showSections 
            ? filterToolSections(this.toolbox, searchList)
            : filterTools(this.toolbox, searchList);
            
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
        hasResults() {
            return this.results && this.results.length > 0;
        },
        toolsetEnabled() {
            return getGalaxyInstance().config.enable_toolset;
        },
        showDetailedView() {
            return this.detailedView;
        },
        getToolsetTools() {
            return filterTools(this.toolbox, this.toolsetIds);
        },
    },
    methods: {
        onQuery(query) {
            this.query = query;
        },
        onResults(results) {
            this.results = results;
            this.queryFilter = this.hasResults ? this.query : null;
            this.setButtonText();
        },
        onPanelResize() {
            //if (this.results) {
            if (this.detailedView) {
                this.savedWidth = parseInt(document.getElementById("left").style["width"]);
                resizePanel(window.innerWidth - this.savedWidth); //change to either hide History Panel or subtract History width
            } else {
                resizePanel(this.savedWidth);
            }
        },
        onFavorites(term) {
            this.query = term;
        },
        onAddFavorite(tool) {
            //todo
        },
        onOpen(tool, evt) {
            const Galaxy = getGalaxyInstance();
            if (tool.id === "upload1") {
                evt.preventDefault();
                Galaxy.upload.show();
            } else if (tool.form_style === "regular") {
                evt.preventDefault();
                Galaxy.router.push("/", { //might use for toolview JULEENNNNN
                    tool_id: tool.id,
                    version: tool.version,
                });
            }
        },
        onToggle() {
            this.showSections = !this.showSections;
            this.setButtonText();
        },
        setButtonText() {
            this.buttonText = this.showSections ? "Hide Sections" : "Show Sections";
        },
        getToolsets() {         
            svc.getToolsetList()
                .then((toolsets) => {
                    toolsets.sort();
                    this.toolsets = this.toolsets.concat(toolsets);
                    console.log("TOOLSETS: ", toolsets, this.toolsets);
                })
                .catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Unable to load list of toolsets.";
                });
        },
        getToolsetToolIds(toolset_id) {
            if (toolset_id != this.mainToolbox) {
                svc.getToolsetToolIds(toolset_id)
                .then((toolIds) => {
                    console.log("\n\nTOOL_IDS: ", toolIds);
                    this.toolsetIds = toolIds;

                })
                .catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Unable to load list of tool ids for selected toolset.";
                });
            } else {
                this.toolsetIds = [];
                //reset to full toolbox
            }
            
        },
    },
    created() {
        this.getToolsets();
    },
};
</script>
