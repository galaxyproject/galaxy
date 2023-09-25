<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye, faEyeSlash } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, type PropType, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import { getAppRoot } from "@/onload/loadConfig";
import { type Tool, type ToolSection as ToolSectionType } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";
import { Workflow, type Workflow as WorkflowType } from "@/stores/workflowStore";
import localize from "@/utils/localization";

import { filterTools, isToolObject } from "./utilities.js";

import ToolSearch from "./Common/ToolSearch.vue";
import ToolSection from "./Common/ToolSection.vue";
import UploadButton from "@/components/Upload/UploadButton.vue";

const SECTION_IDS_TO_EXCLUDE = ["expression_tools"];

const { openGlobalUploadModal } = useGlobalUploadModal();
const router = useRouter();

const emit = defineEmits<{
    (e: "update:show-advanced", showAdvanced: boolean): void;
    (e: "update:panel-query", query: string): void;
    (e: "onInsertTool", toolId: string, toolName: string): void;
    (e: "onInsertModule", moduleName: string, moduleTitle: string | undefined): void;
    (e: "onInsertWorkflow", workflowLatestId: string | undefined, workflowName: string): void;
    (e: "onInsertWorkflowSteps", workflowId: string, workflowStepCount: number | undefined): void;
}>();

const props = defineProps({
    workflow: { type: Boolean, default: false },
    panelView: { type: String, required: true },
    showAdvanced: { type: Boolean, default: false, required: true },
    panelQuery: { type: String, required: true },
    editorWorkflows: { type: Array, default: null },
    dataManagers: { type: Array, default: null },
    moduleSections: { type: Array as PropType<Tool[]>, default: null },
});

library.add(faEye, faEyeSlash);

const queryFilter: Ref<string | null> = ref(null);
const queryPending = ref(false);
const showSections = ref(props.workflow);
const results: Ref<string[]> = ref([]);
const resultPanel: Ref<Record<string, Tool | ToolSectionType> | null> = ref(null);
const buttonText = ref("");
const buttonIcon = ref("");
const closestTerm: Ref<string | null> = ref(null);

const toolStore = useToolStore();

const propShowAdvanced = computed({
    get: () => {
        return props.showAdvanced;
    },
    set: (val: boolean) => {
        emit("update:show-advanced", val);
    },
});
const query = computed({
    get: () => {
        return props.panelQuery;
    },
    set: (q: string) => {
        queryPending.value = true;
        emit("update:panel-query", q);
    },
});

const { currentPanel } = storeToRefs(toolStore);
// const localPanelView = computed(() => (props.setDefault ? props.panelView.value : props.panelView));
const hasResults = computed(() => results.value.length > 0);
// const panelLoaded = computed(() => !!props.panelView && toolStore.panel[props.panelView] !== undefined);
const queryTooShort = computed(() => query.value && query.value.length < 3);
const queryFinished = computed(() => query.value && queryPending.value != true);

const hasDataManagerSection = computed(() => props.workflow && props.dataManagers && props.dataManagers.length > 0);
const dataManagerSection = computed(() => {
    return {
        name: localize("Data Managers"),
        elems: props.dataManagers,
    };
});

/** `toolsById` from `toolStore`, except it only has valid tools for `props.workflow` value */
const localToolsById = computed(() => {
    // Filter the items with is_compat === true
    if (toolStore.toolsById && Object.keys(toolStore.toolsById).length > 0) {
        const toolEntries = Object.entries(toolStore.toolsById).filter(
            ([_, tool]: [string, any]) =>
                !tool.hidden &&
                tool.disabled !== true &&
                (props.workflow ? tool.is_workflow_compatible : !SECTION_IDS_TO_EXCLUDE.includes(tool.panel_section_id))
        );
        return Object.fromEntries(toolEntries);
    }
    return {};
});

/** `currentPanel` from `toolStore`, except it only has valid tools and sections for `props.workflow` value */
const localSectionsById = computed(() => {
    const validToolIdsInCurrentView = Object.keys(localToolsById.value);
    // for all values that are `ToolSection`s, filter out tools that aren't in `localToolsById`
    const sectionEntries = Object.entries(currentPanel.value).map(([id, section]: [string, any]) => {
        if (section.tools && Array.isArray(section.tools)) {
            section.tools = section.tools.filter((tool: string) => validToolIdsInCurrentView.includes(tool));
        }
        return [id, section];
    });

    const updatedSectionEntries = sectionEntries.filter(([id, section]) => {
        if (isToolObject(section) && validToolIdsInCurrentView.includes(id)) {
            // is a `Tool` and is in `localToolsById`
            return true;
        } else if (section.tools === undefined) {
            // is neither a `Tool` nor a `ToolSection`, maybe a `ToolSectionLabel`
            return true;
        } else if (section.tools.length > 0 && (props.workflow || !SECTION_IDS_TO_EXCLUDE.includes(id))) {
            // is a `ToolSection` with tools; check workflow compatibility (based on props.workflow)
            return true;
        } else {
            return false;
        }
    });
    return Object.fromEntries(updatedSectionEntries);
});

const toolsList = computed(() => Object.values(localToolsById.value));

/**
 * If not searching or no results, we show all tools in sections (default)
 *
 * If we have results for search, we show tools in sections or just tools,
 * based on whether `showSections` is true or false
 */
const localPanel = computed(() => {
    if (hasResults.value) {
        if (showSections.value) {
            return resultPanel.value;
        } else {
            return filterTools(localToolsById.value, results.value);
        }
    } else {
        return localSectionsById.value;
    }
});

const sectionIds = computed(() => Object.keys(localPanel.value));

const workflows = computed(() => {
    if (props.workflow && props.editorWorkflows) {
        return props.editorWorkflows;
    } else {
        const Galaxy = getGalaxyInstance();
        const storedWorkflowMenuEntries = Galaxy && Galaxy.config.stored_workflow_menu_entries;
        if (storedWorkflowMenuEntries) {
            const returnedWfs = [];
            if (!props.workflow) {
                returnedWfs.push({
                    title: localize("All workflows"),
                    href: `${getAppRoot()}workflows/list`,
                    id: "list",
                });
            }
            const storedWfs = [
                ...storedWorkflowMenuEntries.map((menuEntry: Workflow) => {
                    return {
                        id: menuEntry.id,
                        title: menuEntry.name,
                        href: `${getAppRoot()}workflows/run?id=${menuEntry.id}`,
                    };
                }),
            ];
            return returnedWfs.concat(storedWfs);
        } else {
            return [];
        }
    }
});

const workflowSection = computed(() => {
    return {
        name: localize("Workflows"),
        elems: workflows.value,
    };
});

function onInsertModule(module: Tool, event: Event) {
    event.preventDefault();
    emit("onInsertModule", module.name, module.title);
}

function onInsertWorkflow(workflow: WorkflowType | Tool, event: Event) {
    event.preventDefault();
    emit("onInsertWorkflow", workflow.latest_id, workflow.name);
}

function onInsertWorkflowSteps(workflow: WorkflowType | Tool) {
    emit("onInsertWorkflowSteps", workflow.id, workflow.step_count);
}

function onToolClick(tool: Tool | WorkflowType, evt: Event) {
    if (!props.workflow) {
        if (tool.id === "upload1") {
            evt.preventDefault();
            openGlobalUploadModal();
        } else if (tool.form_style === "regular") {
            evt.preventDefault();
            // encode spaces in tool.id
            const toolId = tool.id;
            router.push(`/?tool_id=${encodeURIComponent(toolId)}&version=latest`);
        }
    } else {
        evt.preventDefault();
        emit("onInsertTool", tool.id, tool.name);
    }
}

function onResults(
    idResults: string[] | null,
    sectioned: Record<string, Tool | ToolSectionType> | null,
    closestMatch: string | null = null
) {
    if (idResults !== null && idResults.length > 0) {
        results.value = idResults;
        resultPanel.value = sectioned;
        if (sectioned === null) {
            showSections.value = false;
        }
    } else {
        results.value = [];
        resultPanel.value = null;
    }
    closestTerm.value = closestMatch;
    queryFilter.value = hasResults.value ? query.value : null;
    setButtonText();
    queryPending.value = false;
}

function onToggle() {
    showSections.value = !showSections.value;
    setButtonText();
}

function setButtonText() {
    buttonText.value = showSections.value ? localize("Hide Sections") : localize("Show Sections");
    buttonIcon.value = showSections.value ? "fa-eye-slash" : "fa-eye";
}
</script>

<template>
    <div class="unified-panel">
        <div class="unified-panel-controls">
            <ToolSearch
                :enable-advanced="!props.workflow"
                :current-panel-view="props.panelView || ''"
                :placeholder="localize('search tools')"
                :show-advanced.sync="propShowAdvanced"
                :tools-list="toolsList"
                :current-panel="localSectionsById"
                :query="query"
                :query-pending="queryPending"
                @onQuery="(q) => (query = q)"
                @onResults="onResults" />
            <section v-if="!propShowAdvanced">
                <UploadButton />
                <div v-if="hasResults && resultPanel" class="pb-2">
                    <b-button size="sm" class="w-100" @click="onToggle">
                        <FontAwesomeIcon :icon="buttonIcon" />
                        <span class="mr-1">{{ buttonText }}</span>
                    </b-button>
                </div>
                <div v-else-if="queryTooShort" class="pb-2">
                    <b-badge class="alert-danger w-100">Search string too short!</b-badge>
                </div>
                <div v-else-if="queryFinished && !hasResults" class="pb-2">
                    <b-badge class="alert-danger w-100">No results found!</b-badge>
                </div>
                <div v-if="closestTerm" class="pb-2">
                    <b-badge class="alert-danger w-100">
                        Did you mean:
                        <i>
                            <a href="javascript:void(0)" @click="query = closestTerm">{{ closestTerm }}</a>
                        </i>
                        ?
                    </b-badge>
                </div>
            </section>
        </div>
        <div v-if="!propShowAdvanced" class="unified-panel-body">
            <div class="toolMenuContainer">
                <div v-if="localPanel" class="toolMenu">
                    <div v-if="props.workflow">
                        <ToolSection
                            v-for="category in moduleSections"
                            :key="category.name"
                            :hide-name="true"
                            :category="category"
                            tool-key="name"
                            :section-name="category.name"
                            :query-filter="queryFilter"
                            :disable-filter="true"
                            @onClick="onInsertModule" />
                    </div>
                    <ToolSection
                        v-if="hasDataManagerSection"
                        :category="dataManagerSection"
                        :query-filter="queryFilter"
                        :disable-filter="true"
                        @onClick="onToolClick" />
                    <div v-for="(sectionId, key) in sectionIds" :key="key">
                        <ToolSection
                            v-if="localPanel[sectionId]"
                            :category="localPanel[sectionId] || {}"
                            :query-filter="queryFilter"
                            @onClick="onToolClick" />
                    </div>
                </div>
                <div v-if="workflows.length > 0">
                    <ToolSection
                        v-if="props.workflow"
                        :key="workflowSection.name"
                        :category="workflowSection"
                        section-name="workflows"
                        :sort-items="false"
                        operation-icon="fa fa-files-o"
                        operation-title="Insert individual steps."
                        :query-filter="queryFilter"
                        :disable-filter="true"
                        @onClick="onInsertWorkflow"
                        @onOperation="onInsertWorkflowSteps" />
                    <div v-else>
                        <ToolSection :category="{ text: 'Workflows' }" />
                        <div id="internal-workflows" class="toolSectionBody">
                            <div class="toolSectionBg" />
                            <div v-for="wf in workflows" :key="wf.id" class="toolTitle">
                                <a class="title-link" :href="wf.href">{{ wf.title }}</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.toolTitle {
    overflow-wrap: anywhere;
}
</style>
