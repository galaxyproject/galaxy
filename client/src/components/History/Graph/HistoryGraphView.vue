<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import {
    faBezierCurve,
    faBolt,
    faExchangeAlt,
    faExclamationTriangle,
    faMagic,
    faMap,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BNav, BNavItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, toRef, watch } from "vue";

import { usePersistentToggle } from "@/composables/persistentToggle";
import { useHistoryStore } from "@/stores/historyStore";

import { useHistoryGraph } from "./useHistoryGraph";

import HistoryGraphOverview from "./HistoryGraphOverview.vue";
import HistoryGraphReport from "./HistoryGraphReport.vue";
import HistoryGraphToolExecutions from "./HistoryGraphToolExecutions.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import NavigationTitle from "@/components/Common/NavigationTitle.vue";
import HistoryDatasetsBadge from "@/components/History/HistoryDatasetsBadge.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    historyId: string;
    /** Active tab — undefined means the Overview tab. */
    tab?: string;
    seedSrc?: string;
    seedId?: string;
}

const props = defineProps<Props>();

// Data-freshness, projections, SSE subscription — owned by the composable.
const { history, loading, error, focusNodeId, graphNodes, graphEdges, isTruncated, toolExecutionNodes } =
    useHistoryGraph(toRef(props, "historyId"), toRef(props, "seedSrc"), toRef(props, "seedId"));

const historyName = computed(() => history.value?.name ?? "...");

// Whether this is the user's current history — drives the Switch to / Current button.
const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);
const isCurrent = computed(() => currentHistoryId.value === props.historyId);
async function switchHistory() {
    await historyStore.setCurrentHistory(props.historyId);
}

// Collapsible header info block.
const { toggled: headerCollapsed, toggle: toggleHeaderCollapse } = usePersistentToggle(
    "history-graph-header-collapsed",
);

// Tab state is internal — driven by clicks, not by URL changes — so switching
// tabs doesn't change `$route.fullPath` and therefore doesn't trip the
// `<router-view :key="$route.fullPath">` remount in Analysis.vue. The URL's
// `:tab?` param is only used as the initial selection (deep-link entry).
const TABS = [
    { key: "overview", icon: faMap, label: "Overview" },
    { key: "tool-requests", icon: faBolt, label: "Executions" },
    { key: "report", icon: faMagic, label: "Summary" },
] as const;
type TabKey = (typeof TABS)[number]["key"];

function parseTabKey(tab?: string): TabKey {
    return TABS.some((t) => t.key === tab) ? (tab as TabKey) : "overview";
}

const activeTab = ref<TabKey>(parseTabKey(props.tab));

// AI Summary calls an LLM on mount, so keep it lazy until the user actually
// visits the tab at least once. After that it stays mounted (v-show) so the
// fetched report persists across tab switches.
const reportEverActive = ref(activeTab.value === "report");
watch(activeTab, (val) => {
    if (val === "report") {
        reportEverActive.value = true;
    }
});
</script>

<template>
    <div class="history-graph-view">
        <BAlert v-if="error" variant="danger" show>{{ error }}</BAlert>
        <LoadingSpan v-else-if="loading" message="Loading history graph" />
        <BAlert v-else-if="graphNodes.length === 0" show variant="info" class="m-3">
            This history is empty. Add datasets or run tools to populate it.
        </BAlert>
        <BAlert v-else-if="toolExecutionNodes.length === 0" show variant="info" class="m-3">
            No History Graph available. Please ensure that the History contains tool executions, and note that Galaxy
            started capturing the required tool execution data with release 26.1.
        </BAlert>
        <template v-else>
            <NavigationTitle
                :icon="faBezierCurve"
                :title="`History Graph: ${historyName}`"
                heading-description="history graph heading"
                collapsible
                :collapsed="headerCollapsed"
                @toggle="toggleHeaderCollapse">
                <template v-slot:actions>
                    <GButton
                        v-if="isCurrent"
                        disabled
                        size="small"
                        color="blue"
                        tooltip
                        title="This history is your current history">
                        Current
                    </GButton>
                    <GButton
                        v-else
                        size="small"
                        color="blue"
                        tooltip
                        title="Set as current history"
                        @click="switchHistory">
                        <FontAwesomeIcon :icon="faExchangeAlt" fixed-width />
                        Set as Current
                    </GButton>
                </template>
                <template v-slot:collapsible>
                    <div
                        v-if="history"
                        class="history-graph-info px-2 py-1 mt-1 text-muted d-flex justify-content-between align-items-center">
                        <i data-description="history graph time info">
                            <FontAwesomeIcon :icon="faClock" class="mr-1" />
                            <span v-localize>updated</span>
                            <UtcDate :date="history.update_time" mode="elapsed" />
                        </i>
                        <HistoryDatasetsBadge :history-id="historyId" :count="history.count" />
                    </div>
                </template>
            </NavigationTitle>

            <BAlert
                v-if="isTruncated && toolExecutionNodes.length > 0"
                show
                variant="warning"
                class="mt-2 mb-0 py-1 flex-shrink-0">
                <FontAwesomeIcon :icon="faExclamationTriangle" class="mr-1" />
                Only considering first {{ toolExecutionNodes.length }} executions.
            </BAlert>

            <BNav pills class="mb-2 mt-2 p-2 bg-light border-bottom">
                <BNavItem
                    v-for="t in TABS"
                    :key="t.key"
                    :title="t.label"
                    :active="activeTab === t.key"
                    href="#"
                    @click.prevent="activeTab = t.key">
                    <FontAwesomeIcon :icon="t.icon" class="mr-1" />
                    {{ t.label }}
                </BNavItem>
            </BNav>
            <div class="tab-content-container d-flex flex-column overflow-auto">
                <HistoryGraphOverview
                    v-show="activeTab === 'overview'"
                    :nodes="graphNodes"
                    :edges="graphEdges"
                    :focus-node-id="focusNodeId" />
                <HistoryGraphToolExecutions v-show="activeTab === 'tool-requests'" :nodes="toolExecutionNodes" />
                <HistoryGraphReport v-if="reportEverActive" v-show="activeTab === 'report'" :history-id="historyId" />
            </div>
        </template>
    </div>
</template>

<style lang="scss" scoped>
.history-graph-view {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 400px;
}

.tab-content-container {
    flex: 1;
    min-height: 0;
}
</style>
