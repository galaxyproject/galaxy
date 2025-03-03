/**
 * Requests tools, and various panel views
 */

import axios from "axios";
import { defineStore } from "pinia";
import Vue, { computed, type Ref, ref, shallowRef } from "vue";

import { createWhooshQuery, filterTools, type types_to_icons } from "@/components/Panels/utilities";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

export interface FilterSettings {
    [key: string]: string | undefined;
    name?: string;
    section?: string;
    ontology?: string;
    id?: string;
    owner?: string;
    help?: string;
}

export interface Panel {
    id: string;
    model_class: string;
    name: string;
    description: string;
    view_type: keyof typeof types_to_icons;
    searchable: boolean;
}

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
    panel_section_id: string;
    panel_section_name: string | null;
    form_style: string;
    disabled?: boolean;
}

export interface ToolSection {
    model_class: string;
    id: string;
    name: string;
    title?: string;
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

export const useToolStore = defineStore("toolStore", () => {
    const currentPanelView: Ref<string> = useUserLocalStorage("tool-store-view", "");
    const defaultPanelView: Ref<string> = ref("");
    const loading = ref(false);
    const panels = ref<Record<string, Panel>>({});
    const searchWorker = ref<Worker | undefined>(undefined);
    const toolsById = shallowRef<Record<string, Tool>>({});
    const toolResults = ref<Record<string, string[]>>({});
    const toolSections = ref<Record<string, Record<string, Tool | ToolSection>>>({});

    const currentToolSections = computed(() => {
        const effectiveView = currentPanelView.value;
        return toolSections.value[effectiveView] || {};
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

    const getToolForId = computed(() => {
        return (toolId: string) => toolsById.value[toolId];
    });

    const getToolNameById = computed(() => {
        return (toolId: string) => {
            const details = toolsById.value[toolId];
            return details?.name || "...";
        };
    });

    const isPanelPopulated = computed(() => {
        return Object.keys(toolsById.value).length > 0 && Object.keys(currentToolSections.value).length > 0;
    });

    /** These are filtered tool sections (`ToolSection[]`) for the `currentPanel`;
     * Only sections that are typically referenced by `Tool.panel_section_id`
     * are included for the `default` view, while for ontologies, only ontologies are
     * included and `Uncategorized` section is skipped.
     */
    const panelSections = computed(() => {
        return (panelView: string) => {
            return Object.values(toolSections.value[panelView] || {}).filter((section) => {
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

    async function fetchToolSections(panelView: string) {
        try {
            loading.value = true;
            const { data } = await axios.get(`${getAppRoot()}api/tool_panels/${panelView}`);
            saveToolSections(panelView, data);
        } catch (e) {
            rethrowSimple(e);
        } finally {
            loading.value = false;
        }
    }

    async function fetchPanels() {
        try {
            if (!defaultPanelView.value || Object.keys(panels.value).length === 0) {
                const { data } = await axios.get(`${getAppRoot()}api/tool_panels`);
                defaultPanelView.value = data.default_panel_view;
                panels.value = data.views;
            }
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async function fetchToolForId(toolId: string) {
        try {
            const { data } = await axios.get(`${getAppRoot()}api/tools/${toolId}`);
            saveToolForId(toolId, data);
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async function fetchTools(filterSettings?: FilterSettings) {
        try {
            // Backend search
            if (filterSettings && Object.keys(filterSettings).length !== 0) {
                const q = createWhooshQuery(filterSettings);
                if (!toolResults.value[q]) {
                    const { data } = await axios.get(`${getAppRoot()}api/tools`, { params: { q } });
                    saveToolResults(q, data);
                }
            }

            // Fetch all tools by IDs if not already fetched
            if (Object.keys(toolsById.value).length === 0) {
                loading.value = true;
                const { data } = await axios.get(`${getAppRoot()}api/tools?in_panel=False`);
                saveAllTools(data as Tool[]);
            }
        } catch (e) {
            rethrowSimple(e);
        } finally {
            loading.value = false;
        }
    }

    async function initializePanel() {
        try {
            currentPanelView.value = currentPanelView.value || defaultPanelView.value;
            await setPanel(currentPanelView.value);
        } catch (e) {
            await setPanel(defaultPanelView.value);
        }
    }

    function saveAllTools(toolsData: Tool[]) {
        toolsById.value = toolsData.reduce((acc, item) => {
            acc[item.id] = item;
            return acc;
        }, {} as Record<string, Tool>);
    }

    function saveToolSections(panelView: string, newPanel: { [id: string]: ToolSection | Tool }) {
        Vue.set(toolSections.value, panelView, newPanel);
    }

    function saveToolForId(toolId: string, toolData: Tool) {
        Vue.set(toolsById.value, toolId, toolData);
    }

    function saveToolResults(whooshQuery: string, toolsData: Array<string>) {
        Vue.set(toolResults.value, whooshQuery, toolsData);
    }

    async function setPanel(panelView: string) {
        try {
            if (!toolSections.value[panelView]) {
                await fetchToolSections(panelView);
            }
            currentPanelView.value = panelView;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    return {
        currentPanelView,
        currentToolSections,
        defaultPanelView,
        fetchToolSections,
        fetchPanels,
        fetchToolForId,
        fetchTools,
        initializePanel,
        isPanelPopulated,
        loading,
        getToolForId,
        getToolNameById,
        getToolsById,
        panels,
        saveAllTools,
        saveToolForId,
        saveToolResults,
        saveToolSections,
        searchWorker,
        sectionDatalist,
        setPanel,
        toolsById,
        toolSections,
    };
});
