<template>
    <ToolsProvider
        v-slot="{ loading, result: itemsLoaded, count: totalItems }"
        :filter-settings="filterSettings"
        :show-help="showHelp === 'true'">
        <section>
            <div class="mb-2">
                <span class="row">
                    <span class="col">
                        <h4 class="d-inline-block align-middle">Advanced Tool Search Results</h4>
                        <b-button v-if="hasFilters" class="float-right" size="sm" @click="onClear">
                            <icon icon="redo" />
                            <span>{{ "Clear Search" | localize }}</span>
                        </b-button>
                    </span>
                </span>
                <span v-if="itemsLoaded.length !== 0 && hasFilters" class="row">
                    <span class="col"> (found {{ itemsLoaded.length }} of {{ totalItems }} tools) </span>
                </span>
            </div>
            <div>
                <b-alert v-if="loading" class="m-2" variant="info" show>
                    <LoadingSpan message="Loading Advanced Search Results" />
                </b-alert>
                <b-alert v-else-if="!hasFilters" class="m-2" variant="secondary" show>
                    There are no valid filters applied. Please add filters to the menu in the Tool Panel.
                </b-alert>
                <b-alert v-else-if="!itemsLoaded || itemsLoaded.length == 0" class="m-2" variant="danger" show>
                    No tools found for selected filter(s): {{ filterSettings }}
                </b-alert>
                <div v-else>
                    <b-card v-for="(tool, key) in itemsLoaded" :key="key" no-body>
                        <b-card-header
                            v-b-toggle="'accordion-' + key"
                            :disabled="!hasHelp(tool.help)"
                            :role="hasHelp(tool.help) ? 'button' : ''">
                            <span class="pl-2 d-flex justify-content-between">
                                <span class="row">
                                    <a
                                        :href="tool.target === 'galaxy_main' ? 'javascript:void(0)' : tool.link"
                                        @click.stop="onOpen(tool)">
                                        <b>{{ tool.name }}</b> {{ tool.description }}
                                    </a>
                                    <b-badge class="ml-1">{{ tool.panel_section_name }}</b-badge>
                                    <b-badge
                                        v-if="tool.is_workflow_compatible"
                                        v-b-tooltip.hover
                                        class="ml-1"
                                        variant="success"
                                        title="Can use this tool in Workflows"
                                        >Workflow</b-badge
                                    >
                                    <b-badge v-if="tool.hidden" class="ml-1" variant="danger">Hidden</b-badge>
                                </span>
                                <i v-if="hasHelp(tool.help)" class="text-secondary"> Click here to expand tool info </i>
                            </span>
                        </b-card-header>
                        <b-collapse :id="'accordion-' + key" role="tabpanel">
                            <b-card-body>
                                <p
                                    v-if="helpSummary(tool.help)"
                                    :id="'collapseInfo-' + key"
                                    class="collapse show"
                                    v-html="helpSummary(tool.help)"></p>
                                <a
                                    v-if="helpSummary(tool.help)"
                                    data-toggle="collapse"
                                    :href="'#collapseInfo-' + key"
                                    role="button"
                                    aria-expanded="false"
                                    :aria-controls="'collapseInfo-' + key">
                                    Show more/less
                                </a>
                                <p
                                    :id="'collapseInfo-' + key"
                                    :class="helpSummary(tool.help) ? 'collapse' : ''"
                                    v-html="tool.help"></p>
                            </b-card-body>
                        </b-collapse>
                    </b-card>
                </div>
                <b-button
                    v-if="hasFilters && !loading && offset > 200"
                    v-b-tooltip.hover
                    class="btn-back-to-top"
                    title="Scroll To Top"
                    variant="danger"
                    pill
                    size="lg"
                    @click="scrollToTop">
                    <icon icon="arrow-up" />
                </b-button>
            </div>
        </section>
    </ToolsProvider>
</template>
<script>
import { getGalaxyInstance } from "app";
import LoadingSpan from "components/LoadingSpan";
import { openGlobalUploadModal } from "components/Upload";
import { ToolsProvider } from "components/providers/storeProviders";

export default {
    components: {
        LoadingSpan,
        ToolsProvider,
    },
    props: {
        name: {
            type: String,
            default: "",
        },
        panelSectionName: {
            type: String,
            default: "",
        },
        id: {
            type: String,
            default: "",
        },
        description: {
            type: String,
            default: "",
        },
        showHelp: {
            type: String,
            default: "false",
        },
        help: {
            type: String,
            default: "",
        },
    },
    data() {
        return {
            offset: 0,
        };
    },
    computed: {
        filterSettings() {
            const newFilterSettings = {};
            Object.entries(this.$props).forEach(([filter, value]) => {
                if (value && value !== "") {
                    if (filter === "panelSectionName") {
                        newFilterSettings["panel_section_name"] = value;
                    } else if (filter !== "showHelp") {
                        newFilterSettings[filter] = value;
                    }
                }
            });
            return newFilterSettings;
        },
        hasFilters() {
            return Object.keys(this.filterSettings).length;
        },
    },
    beforeDestroy() {
        document.querySelector(".center-panel").removeEventListener("scroll", this.onScroll, true);
    },
    mounted() {
        document.querySelector(".center-panel").addEventListener("scroll", this.onScroll, true);
    },
    methods: {
        onScroll(e) {
            this.offset = e.target.scrollTop;
        },
        hasHelp(help) {
            return help && help !== "\n";
        },
        onClear() {
            this.$router.push({ path: "/tools/advanced_search" });
        },
        onOpen(tool) {
            if (tool.id === "upload1") {
                openGlobalUploadModal();
            } else if (tool.form_style === "regular") {
                const Galaxy = getGalaxyInstance();
                // encode spaces in tool.id
                const toolId = tool.id;
                const toolVersion = tool.version;
                Galaxy.router.push(`/?tool_id=${encodeURIComponent(toolId)}&version=${toolVersion}`);
            }
        },
        scrollToTop() {
            document.querySelector(".center-panel").scrollTop = 0;
        },
        helpSummary(help) {
            const parser = new DOMParser();
            const helpDoc = parser.parseFromString(help, "text/html");
            const xpaths = [
                "//strong[text()='What it does']/../following-sibling::*",
                "//strong[text()='What It Does']/../following-sibling::*",
                "//h1[text()='Synopsis']/following-sibling::*",
                "//strong[text()='Syntax']/../following-sibling::*",
            ];
            const matches = [];
            xpaths.forEach((xpath) => {
                matches.push(
                    helpDoc.evaluate(xpath, helpDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue
                );
            });
            let returnVal = null;
            matches.forEach((match) => {
                if (match) {
                    returnVal = match.innerHTML + "\n";
                }
            });
            return returnVal;
        },
    },
};
</script>

<style>
.btn-back-to-top {
    position: fixed;
    bottom: 2em;
}
</style>
