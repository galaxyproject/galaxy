<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { watchEffect } from "vue";

import { type Tool, useToolStore } from "@/stores/toolStore";

import LoadingSpan from "../LoadingSpan.vue";
import ScrollList from "../ScrollList/ScrollList.vue";
import ToolsListCard from "./ToolsListCard.vue";

/** Number of tools to fetch the help data for at a time. */
const FETCH_LIMIT = 4;

/** Number of tools to prefetch help data for beyond the current offset. */
const PREFETCH_AHEAD = 8;

const props = defineProps<{
    tools: Tool[];
    loading?: boolean;
    hasOwnerFilter?: boolean;
}>();

const toolStore = useToolStore();
const { helpDataCached } = storeToRefs(toolStore);

async function loadTools(offset: number, limit: number): Promise<{ items: Tool[]; total: number }> {
    const items = props.tools.slice(offset, offset + limit);

    // Fetch help data for the latest batch
    const helpPromises = items.map((tool) => toolStore.fetchHelpForId(tool.id));
    await Promise.all(helpPromises);

    // We prefetch help data for the next PREFETCH_AHEAD tools, so it's already ready when the user scrolls
    const nextOffset = offset + limit;
    const nextItems = props.tools.slice(nextOffset, nextOffset + PREFETCH_AHEAD);
    if (nextItems.length > 0) {
        Promise.all(nextItems.map((tool) => toolStore.fetchHelpForId(tool.id)));
    }

    return { items, total: props.tools.length };
}

// Watch for changes in tools array to preload initial help data
watchEffect(() => {
    if (props.tools.length > 0) {
        const initialItems = props.tools.slice(0, FETCH_LIMIT + PREFETCH_AHEAD);
        Promise.all(initialItems.map((tool) => toolStore.fetchHelpForId(tool.id)));
    }
});
</script>

<template>
    <ScrollList
        ref="root"
        :loader="loadTools"
        :limit="FETCH_LIMIT"
        :item-key="(tool) => tool.id"
        :prop-total-count="props.tools.length"
        :prop-busy="props.loading"
        name="tool"
        name-plural="tools"
        :load-disabled="!props.tools.length"
        show-count-in-footer>
        <template v-slot:loading>
            <BAlert v-if="props.tools.length" show>
                <LoadingSpan message="Loading tools" />
            </BAlert>
        </template>

        <template v-slot:item="{ item }">
            <ToolsListCard
                :id="item.id"
                :key="item.id"
                :name="item.name"
                :section="item.panel_section_name || undefined"
                :edam-operations="item.edam_operations"
                :edam-topics="item.edam_topics"
                :description="item.description"
                :fetching="!helpDataCached[item.id]"
                :form-style="item.form_style"
                :summary="helpDataCached[item.id]?.summary"
                :help="helpDataCached[item.id]?.help"
                :local="item.target === 'galaxy_main'"
                :link="item.link"
                :owner="props.hasOwnerFilter && item.tool_shed_repository ? item.tool_shed_repository.owner : undefined"
                :workflow-compatible="item.is_workflow_compatible"
                :version="item.version"
                @apply-filter="(filter, value) => $emit('apply-filter', filter, value)" />
        </template>
    </ScrollList>
</template>
