<script setup lang="ts">
import { ref, watch } from "vue";

import type { Tool } from "@/stores/toolStore";

import { fetchData } from "./services";

import ScrollList from "../ScrollList/ScrollList.vue";
import ToolsListItem from "./ToolsListItem.vue";

/** Number of tools to fetch the help data for at a time. */
const FETCH_LIMIT = 20;

type ToolHelpData = {
    help?: string;
    summary?: string;
};

const props = defineProps<{
    tools: Tool[];
    loading?: boolean;
    hasOwnerFilter?: boolean;
}>();

const busy = ref(false);
const helpDataCached = ref<Map<string, ToolHelpData>>(new Map());
const toolsUptoOffset = ref<Tool[]>([]);

async function loadTools(offset: number, limit: number): Promise<{ items: Tool[]; total: number }> {
    busy.value = true;

    const items = props.tools.slice(offset, offset + limit);

    toolsUptoOffset.value.push(...items);

    for (const tool of items) {
        if (!helpDataCached.value.has(tool.id)) {
            await fetchHelp(tool);
        }
    }

    busy.value = false;

    return { items, total: props.tools.length };
}

watch(
    () => props.tools,
    async () => {
        toolsUptoOffset.value = [];
        await loadTools(0, FETCH_LIMIT);
    },
    { deep: true }
);

async function fetchHelp(tool: Tool) {
    try {
        const toolHelpData: ToolHelpData = {};

        const response = await fetchData(`api/tools/${encodeURIComponent(tool.id)}/build`);

        const help = response.help;
        if (help && help !== "\n") {
            toolHelpData.help = help;
            toolHelpData.summary = parseHelpForSummary(help);
        } else {
            toolHelpData.help = ""; // for cases where helpText == '\n'
        }

        helpDataCached.value.set(tool.id, toolHelpData);
    } catch (error) {
        console.error("Error fetching help:", error);
    }
}

/** Given the help text, extracts and returns a summary by detecting relevant HTML elements
 * that could contain a short description of the tool.
 */
function parseHelpForSummary(help: string): string {
    let summary = "";
    const parser = new DOMParser();
    const helpDoc = parser.parseFromString(help, "text/html");

    const terms = ["what it does", "synopsis", "syntax", "purpose"];
    const xpaths: string[] = [];

    // Generate XPath expressions for each term
    terms.forEach((term) => {
        // Case-insensitive strong element check
        xpaths.push(
            `//strong[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ?', 'abcdefghijklmnopqrstuvwxyz'), '${term}')]/../following-sibling::*`
        );

        // Case-sensitive h1 element check (capitalize first letter)
        const capitalizedTerm = term.charAt(0).toUpperCase() + term.slice(1);
        xpaths.push(`//h1[text()='${capitalizedTerm}']/following-sibling::*`);
    });

    const matches: Node[] = [];
    xpaths.forEach((xpath) => {
        const newNode = helpDoc.evaluate(
            xpath,
            helpDoc,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        ).singleNodeValue;
        if (newNode) {
            matches.push(newNode);
        }
    });

    matches.forEach((match) => {
        if (match) {
            summary += (match as HTMLElement).innerHTML + "\n";
        }
    });
    return summary;
}
</script>

<template>
    <ScrollList
        :loader="loadTools"
        :limit="FETCH_LIMIT"
        :item-key="(tool) => tool.id"
        :prop-items="toolsUptoOffset"
        :prop-total-count="props.tools.length"
        :prop-busy="busy || (!props.tools.length && props.loading)"
        name="tool"
        name-plural="tools"
        :load-disabled="!props.tools.length">
        <template v-slot:item="{ item }">
            <ToolsListItem
                :id="item.id"
                :key="item.id"
                :name="item.name"
                :section="item.panel_section_name || undefined"
                :edam-operations="item.edam_operations"
                :edam-topics="item.edam_topics"
                :description="item.description"
                :fetching="!helpDataCached.has(item.id) && busy"
                :form-style="item.form_style"
                :summary="helpDataCached.get(item.id)?.summary"
                :help="helpDataCached.get(item.id)?.help"
                :local="item.target === 'galaxy_main'"
                :link="item.link"
                :owner="props.hasOwnerFilter && item.tool_shed_repository ? item.tool_shed_repository.owner : undefined"
                :workflow-compatible="item.is_workflow_compatible"
                :version="item.version"
                @apply-filter="(filter, value) => $emit('apply-filter', filter, value)" />
        </template>
    </ScrollList>
</template>

<style lang="scss" scoped>
:deep(.scroll-list-container) {
    .list-group {
        gap: 1rem;
    }
}
</style>
