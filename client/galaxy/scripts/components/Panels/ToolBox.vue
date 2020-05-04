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
                    <option v-for="toolset in toolsets" v-bind:key="toolset" v-on:click="getToolsetToolIds(toolset)">
                        {{ toolset }}
                    </option>
                </select>

            </div>
            <tool-search :query="query" placeholder="search tools" @onQuery="onQuery" @onResults="onResults" />

            <div class="py-2" v-if="hasResults">
                <b-button @click="onToggle">{{ buttonText }}</b-button>
            </div>
            <div class="py-2" v-else-if="query">
                <span v-if="query.length < 3" class="font-weight-bold">***Search string too short***</span>
                <span v-else class="font-weight-bold">***No Results Found***</span>
            </div>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
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
import axios from "axios";
import ToolSection from "./Common/ToolSection";
import ToolSearch from "./Common/ToolSearch";
import UploadButton from "./Buttons/UploadButton";
import FavoritesButton from "./Buttons/FavoritesButton";
import { filterToolSections, filterTools, resizePanel } from "./utilities";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import svc from "./service";
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
            queryFilter: null,
            showSections: false,
            buttonText: "",
            toolsets: ["None"],
            toolsetIds: [],
            selected: "None",
            savedWidth: null,
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
            // what happens when searching a toolset? still just displays selected toolset
            if (this.toolsetIds.length > 0 && this.selected != "None") {
                return filterToolSections(this.toolbox, this.toolsetIds);
                //idea: get list of uninstalled tools that are in toolset and suggest installing them/contact admin
            }
            else if (this.showSections) {
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
            return true;
            //return getGalaxyInstance().config.enable_toolsets; //make configurable feature?
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
            this.onResultsResize();
        },
        onResultsResize() {
            if (this.results) {
                this.savedWidth = parseInt(document.getElementById("left").style["width"]);
                resizePanel(this.savedWidth * 2);
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
                Galaxy.router.push("/", {
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
                })
                /*.catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Unable to load list of toolsets.";
                })*/;
        },
        getToolsetToolIds(toolset_id) {
            console.log("\nTOOLSET_ID: ", toolset_id);

            if (toolset_id != "None") {
                svc.getToolsetToolIds(toolset_id)
                .then((toolIds) => {
                    console.log("\n\nTOOL_IDS: ", toolIds);
                    this.toolsetIds = toolIds;
                    //this.filterToolsetTools(toolsIds);
                    //return filterToolSections(this.toolbox, toolsIds);
                    /* add option to see other tools in the toolset that are not installed. to have tools installed, contact your Galaxy admin*/

                })
                /*.catch((error) => {
                    this.messageVariant = "danger";
                    const message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Unable to load list of toolsets.";
                })*/;
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
