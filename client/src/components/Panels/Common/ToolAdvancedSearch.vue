<template>
    <ToolsProvider v-slot="{ loading, result: itemsLoaded, count: totalItems }" :filter-settings="filterSettings">
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
                <span v-if="itemsLoaded.length !== 0" class="row">
                    <span v-if="hasFilters" class="col">
                        (found {{ itemsLoaded.length }} of {{ totalItems }} tools)
                    </span>
                    <span v-else class="col">(showing all {{ totalItems }} tools)</span>
                </span>
            </div>
            <div>
                <b-alert v-if="loading" class="m-2" variant="info" show>
                    <LoadingSpan message="Loading Advanced Search Results" />
                </b-alert>
                <b-alert v-else-if="!itemsLoaded || itemsLoaded.length == 0" class="m-2" variant="danger" show>
                    No tools found for selected filter(s).
                </b-alert>
                <div v-else>
                    <tool-section
                        v-for="(section, key) in itemsLoaded"
                        :key="key"
                        :category="section"
                        @onClick="onOpen" />
                </div>
            </div>
        </section>
    </ToolsProvider>
</template>
<script>
import { getGalaxyInstance } from "app";
import LoadingSpan from "components/LoadingSpan";
import { openGlobalUploadModal } from "components/Upload";
import { ToolsProvider } from "components/providers/storeProviders";
import ToolSection from "components/Panels/Common/ToolSection";

export default {
    components: {
        LoadingSpan,
        ToolsProvider,
        ToolSection,
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
    },
    computed: {
        filterSettings() {
            const newFilterSettings = {};
            Object.entries(this.$props).forEach(([filter, value]) => {
                if (value && value !== "") {
                    if (filter === "panelSectionName") {
                        newFilterSettings["panel_section_name"] = value;
                    } else {
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
    methods: {
        onClear() {
            this.$router.push({ path: "/tools/advanced_search", query: {} });
        },
        onOpen(tool, evt) {
            if (tool.id === "upload1") {
                evt.preventDefault();
                openGlobalUploadModal();
            } else if (tool.form_style === "regular") {
                evt.preventDefault();
                const Galaxy = getGalaxyInstance();
                // encode spaces in tool.id
                const toolId = tool.id;
                const toolVersion = tool.version;
                Galaxy.router.push(`/?tool_id=${encodeURIComponent(toolId)}&version=${toolVersion}`);
            }
        },
    },
};
</script>
