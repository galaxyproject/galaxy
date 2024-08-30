/**
 * Requests tools, and various panel views
 */

import axios from "axios";
import { defineStore } from "pinia";
import Vue, { computed, type Ref, ref, shallowRef } from "vue";

import type { PanelView } from "@/components/Panels/utilities";
import { createWhooshQuery, filterTools } from "@/components/Panels/utilities";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

import type { FilterSettings, Tool, ToolSection } from "./toolStoreTypes";

export const useToolStore = defineStore("toolStore", () => {
    const currentPanelView: Ref<string> = useUserLocalStorage("tool-store-view", "");
    const defaultPanelView: Ref<string> = ref("");
    const toolsById = shallowRef<Record<string, Tool>>({});
    const toolResults = ref<Record<string, string[]>>({});
    const panel = ref<Record<string, Record<string, Tool | ToolSection>>>({});
    const panelViews = ref<Record<string, PanelView>>({});
    const loading = ref(false);

    const searchWorker = ref<Worker | undefined>(undefined);

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
                .get(`${getAppRoot()}api/tools?in_panel=False`)
                .then(({ data }) => {
                    saveAllTools(data as Tool[]);
                    loading.value = false;
                })
                .catch((error) => {
                    console.error(error);
                    loading.value = false;
                });
        }
    }

    async function fetchPanelViews() {
        if (loading.value || (defaultPanelView.value && Object.keys(panelViews.value).length > 0)) {
            return;
        }
        loading.value = true;
        try {
            const { data } = await axios.get(`${getAppRoot()}api/tool_panels`);
            const { default_panel_view, views } = data;
            defaultPanelView.value = default_panel_view;
            panelViews.value = views;
        } catch (e) {
            rethrowSimple(e);
        } finally {
            loading.value = false;
        }
    }

    // Used to initialize the ToolPanel with the default panel view for this site.
    async function initCurrentPanelView(siteDefaultPanelView: string) {
        if (!loading.value && !isPanelPopulated.value) {
            loading.value = true;
            const panelView = currentPanelView.value || siteDefaultPanelView;
            if (currentPanelView.value == "") {
                currentPanelView.value = panelView;
            }
            await axios
                .get(`${getAppRoot()}api/tool_panels/${panelView}`)
                .then(({ data }) => {
                    loading.value = false;
                    savePanelView(panelView, data);
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
            if (panel.value[panelView]) {
                currentPanelView.value = panelView;
                return;
            }
            loading.value = true;
            try {
                const { data } = await axios.get(`${getAppRoot()}api/tool_panels/${panelView}`);
                currentPanelView.value = panelView;
                savePanelView(panelView, data);
                loading.value = false;
            } catch (e) {
                const error = e as { response: { data: { err_msg: string } } };
                console.error("Could not change panel view", error.response.data.err_msg ?? error.response);
                loading.value = false;
            }
        }
    }

    async function fetchPanel(panelView: string) {
        const { data } = await axios.get(`${getAppRoot()}api/tool_panels/${panelView}`);
        savePanelView(panelView, data);
    }

    function saveToolForId(toolId: string, toolData: Tool) {
        Vue.set(toolsById.value, toolId, toolData);
    }

    function saveToolResults(whooshQuery: string, toolsData: Array<string>) {
        Vue.set(toolResults.value, whooshQuery, toolsData);
    }

    function saveAllTools(toolsData: Tool[]) {
        toolsById.value = toolsData.reduce((acc, item) => {
            acc[item.id] = item;
            return acc;
        }, {} as Record<string, Tool>);
    }

    function savePanelView(panelView: string, newPanel: { [id: string]: ToolSection | Tool }) {
        Vue.set(panel.value, panelView, newPanel);
    }

    return {
        toolsById,
        panel,
        panelViews,
        currentPanelView,
        defaultPanelView,
        loading,
        getToolForId,
        getToolNameById,
        getToolsById,
        currentPanel,
        isPanelPopulated,
        sectionDatalist,
        searchWorker,
        fetchToolForId,
        fetchTools,
        fetchPanelViews,
        initCurrentPanelView,
        setCurrentPanelView,
        fetchPanel,
        saveToolForId,
        saveToolResults,
        saveAllTools,
        savePanelView,
    };
});
