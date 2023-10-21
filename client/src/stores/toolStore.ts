/**
 * Requests tools, and various panel views
 */

import axios from "axios";
import { defineStore } from "pinia";
import Vue, { computed, Ref, ref } from "vue";

import { createWhooshQuery, filterTools } from "@/components/Panels/utilities";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { getAppRoot } from "@/onload/loadConfig";

export interface Tool {
    model_class: string;
    id: string;
    name: string;
    version: string;
    description: string;
    labels: string[];
    edam_operations: string[];
    edam_topics: string[];
    hidden: "" | boolean;
    is_workflow_compatible: boolean;
    xrefs: string[];
    config_file: string;
    link: string;
    min_width: number;
    target: string;
    panel_section_id: string | null;
    panel_section_name: string | null;
    form_style: string;
    disabled?: boolean;
}

export interface ToolSection {
    model_class: string;
    id: string;
    name: string;
    version?: string;
    description?: string;
    links?: Record<string, string>;
    tools?: (string | ToolSectionLabel)[];
    elems?: (Tool | ToolSection)[];
}

export interface ToolSectionLabel {
    model_class: string;
    id: string;
    text: string;
    version?: string;
    description?: string | null;
    links?: Record<string, string> | null;
}

export interface FilterSettings {
    [key: string]: string | undefined;
    name?: string;
    section?: string;
    ontology?: string;
    id?: string;
    owner?: string;
    help?: string;
}

export const useToolStore = defineStore("toolStore", () => {
    const currentPanelView: Ref<string> = useUserLocalStorage("tool-store-view", "");
    const toolsById = ref<Record<string, Tool>>({});
    const toolResults = ref<Record<string, string[]>>({});
    const panel = ref<Record<string, Record<string, Tool | ToolSection>>>({});
    const loading = ref(false);

    const getToolForId = computed(() => {
        return (toolId: string) => toolsById.value[toolId];
    });

    const getToolNameById = computed(() => {
        return (toolId: string) => {
            const details = toolsById.value[toolId];
            if (details && details.name) {
                return details.name;
            } else {
                return "...";
            }
        };
    });

    const getToolsById = computed(() => {
        return (filterSettings: FilterSettings) => {
            if (Object.keys(filterSettings).length === 0) {
                return toolsById.value;
            } else {
                const q = createWhooshQuery(filterSettings);
                return filterTools(toolsById.value, toolResults.value[q] || []);
            }
        };
    });

    const currentPanel = computed(() => {
        const effectiveView = currentPanelView.value;
        const val = panel.value[effectiveView] || {};
        return val;
    });

    const isPanelPopulated = computed(() => {
        return allToolsByIdFetched.value && Object.keys(currentPanel.value).length > 0;
    });

    const allToolsByIdFetched = computed(() => {
        return Object.keys(toolsById.value).length > 0;
    });

    /** These are filtered tool sections (`ToolSection[]`) for the `currentPanel`;
     * Only sections that are typically referenced by `Tool.panel_section_id`
     * are included for the `default` view, while for ontologies, only ontologies are
     * included and `Uncategorized` section is skipped.
     */
    const panelSections = computed(() => {
        return (panelView: string) => {
            return Object.values(panel.value[panelView] || {}).filter((section) => {
                const sec = section as ToolSection;
                return (
                    sec.tools &&
                    sec.tools.length > 0 &&
                    sec.id !== "uncategorized" &&
                    sec.id !== "builtin_converters" &&
                    sec.name !== undefined
                );
            });
        };
    });
    const sectionDatalist = computed(() => {
        return (panelView: string) => {
            return panelSections.value(panelView).map((section) => {
                return { value: section.id, text: section.name };
            });
        };
    });

    async function fetchToolForId(toolId: string) {
        console.log("fetching tool");
        const { data } = await axios.get(`${getAppRoot()}api/tools/${toolId}`);
        saveToolForId(toolId, data);
    }

    async function fetchTools(filterSettings?: FilterSettings) {
        if (filterSettings && Object.keys(filterSettings).length !== 0) {
            // Parsing filterSettings to Whoosh query
            const q = createWhooshQuery(filterSettings);
            // already have results for this query
            if (toolResults.value[q]) {
                return;
            }
            const { data } = await axios.get(`${getAppRoot()}api/tools`, { params: { q } });
            saveToolResults(q, data);
        }
        if (!loading.value && !allToolsByIdFetched.value) {
            loading.value = true;
            await axios
                .get(`${getAppRoot()}api/tool_panel?in_panel=False`)
                .then(({ data }) => {
                    saveAllTools(data.tools);
                    loading.value = false;
                })
                .catch((error) => {
                    console.error(error);
                    loading.value = false;
                });
        }
    }

    // Directly related to the ToolPanel
    async function initCurrentPanelView(siteDefaultPanelView: string) {
        if (!loading.value && !isPanelPopulated.value) {
            loading.value = true;
            const panelView = currentPanelView.value || siteDefaultPanelView;
            if (currentPanelView.value == "") {
                currentPanelView.value = panelView;
            }
            await axios
                .get(`${getAppRoot()}api/tool_panel?in_panel=true&view=${panelView}`)
                .then(({ data }) => {
                    loading.value = false;
                    savePanelView(panelView, data[panelView]);
                })
                .catch(async (error) => {
                    loading.value = false;
                    if (error.response && error.response.status == 400) {
                        // Assume the stored panelView disappeared, revert to the panel default for this site.
                        await setCurrentPanelView(siteDefaultPanelView);
                    }
                });
        }
    }

    async function setCurrentPanelView(panelView: string) {
        if (!loading.value) {
            currentPanelView.value = panelView;
            if (panel.value[panelView]) {
                return;
            }
            loading.value = true;
            const { data } = await axios.get(`${getAppRoot()}api/tool_panel?in_panel=true&view=${panelView}`);
            savePanelView(panelView, data[panelView]);
            loading.value = false;
        }
    }

    async function fetchPanel(panelView: string) {
        const { data } = await axios.get(`${getAppRoot()}api/tool_panel?in_panel=true&view=${panelView}`);
        savePanelView(panelView, data[panelView]);
    }

    function saveToolForId(toolId: string, toolData: Tool) {
        Vue.set(toolsById.value, toolId, toolData);
    }

    function saveToolResults(whooshQuery: string, toolsData: Array<string>) {
        Vue.set(toolResults.value, whooshQuery, toolsData);
    }

    function saveAllTools(toolsData: Record<string, Tool>) {
        toolsById.value = toolsData;
    }

    function savePanelView(panelView: string, newPanel: { [id: string]: ToolSection | Tool }) {
        Vue.set(panel.value, panelView, newPanel);
    }

    return {
        toolsById,
        panel,
        currentPanelView,
        loading,
        getToolForId,
        getToolNameById,
        getToolsById,
        currentPanel,
        isPanelPopulated,
        sectionDatalist,
        fetchToolForId,
        fetchTools,
        initCurrentPanelView,
        setCurrentPanelView,
        fetchPanel,
        saveToolForId,
        saveToolResults,
        saveAllTools,
        savePanelView,
    };
});
