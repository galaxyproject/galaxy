<template>
    <div :step-label="model.step_label">
        <FormCard v-model:expanded="expanded" :title="model.fixed_title" :icon="icon" :collapsible="true">
            <template v-slot:body>
                <FormDisplay
                    v-if="hasInputs"
                    :inputs="inputs"
                    :validation-scroll-to="formValidationScrollTo"
                    @onChange="onChange"
                    @onValidation="onValidation"
                    @load-more="onLoadMore"
                    @search-change="onSearchChange" />
                <div v-else class="py-2">No options available.</div>
            </template>
        </FormCard>
    </div>
</template>

<script setup lang="ts">
import { debounce } from "lodash";
import { computed, onBeforeUnmount, ref, watch } from "vue";

import type { HistoryItemSummary } from "@/api";
import type { FormData, FormInputNode } from "@/components/Form/composables/useFormState";
import type { DataOption } from "@/components/Form/Elements/FormData/types";
import { DEFAULT_OPTIONS_PAGE_SIZE } from "@/components/Form/Elements/FormData/types";
import WorkflowIcons from "@/components/Workflow/icons";

import { searchHistoryContents } from "./services";

import FormCard from "@/components/Form/FormCard.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";

type PaginatedDataOption = Pick<DataOption, "id" | "src" | "name" | "hid" | "keep" | "tags">;
type StepInput = FormInputNode & Record<string, any>;

interface Props {
    /**
     * Workflow run step, an entry of ``WorkflowRunModel.steps``
     */
    model: Record<string, any>;
    /**
     * ``[inputName, message]`` of the invalid input to scroll to, or empty
     */
    validationScrollTo: [string, string] | [];
    /**
     * History searched for paginated data options
     * @default null
     */
    historyId?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
    historyId: null,
});

const emit = defineEmits<{
    (e: "onChange", index: string, data: FormData): void;
    (e: "onValidation", index: string, validation: [string, string] | null): void;
}>();

const expanded = ref<boolean>(props.model.expanded);
// Local copy so pagination can replace ``options`` without mutating the prop.
const localInputs = ref<StepInput[]>(buildLocalInputs());

const icon = computed(() => (WorkflowIcons as Record<string, string>)[props.model.step_type]);

const inputs = computed(() => localInputs.value);

const hasInputs = computed(() => inputs.value.length > 0);

// FormDisplay takes null rather than an empty array.
const formValidationScrollTo = computed(() =>
    props.validationScrollTo.length === 2 ? props.validationScrollTo : null,
);

function isSimpleInputType(stepType: string) {
    return stepType.startsWith("data_input") || stepType.startsWith("data_collection_input");
}

function buildLocalInputs(): StepInput[] {
    return (props.model.inputs || []).map((input: StepInput) => ({
        ...input,
        flavor: "module",
        hide_label: isSimpleInputType(props.model.step_type),
    }));
}

function onChange(data: FormData) {
    emit("onChange", props.model.index, data);
}

function onValidation(validation: [string, string] | null) {
    emit("onValidation", props.model.index, validation);
}

function findInputByName(name: string) {
    return localInputs.value.find((i) => i.name === name);
}

function shapeContentsRow(row: HistoryItemSummary): PaginatedDataOption {
    const src = row.history_content_type === "dataset_collection" ? "hdca" : "hda";
    return {
        id: row.id,
        src,
        name: row.name ?? "",
        hid: row.hid,
        keep: false,
        tags: row.tags || [],
    };
}

async function fetchStepOptions(
    name: string,
    src: string,
    payload: { offset?: number; limit?: number; search?: string } = {},
) {
    const input = findInputByName(name);
    if (!input || !props.historyId) {
        return;
    }
    const type = src === "hdca" ? "dataset_collection" : "dataset";
    const extensions = input.acceptable_extensions || [];
    const limit = payload.limit || DEFAULT_OPTIONS_PAGE_SIZE;
    const offset = payload.offset || 0;
    try {
        const rows = await searchHistoryContents(props.historyId, {
            extensions,
            type,
            tag: input.tag,
            // ``data_collection`` parameters offer hidden collections too.
            visibleOnly: input.type !== "data_collection",
            search: payload.search,
            offset,
            limit,
        });
        const shaped: PaginatedDataOption[] = (rows || []).map(shapeContentsRow);
        const base = (input.options as Record<string, PaginatedDataOption[]> | undefined)?.[src] || [];
        const seen = new Set(base.map((item) => `${item.id}_${item.src}`));
        const merged = base.concat(
            shaped.filter((item) => {
                const key = `${item.id}_${item.src}`;
                if (seen.has(key)) {
                    return false;
                }
                seen.add(key);
                return true;
            }),
        );
        input.options = { ...(input.options || {}), [src]: merged };
        input.options_meta = {
            ...(input.options_meta || {}),
            [src]: { offset, limit, has_more: shaped.length === limit },
        };
        // FormDisplay only syncs server-owned attributes when the inputs prop changes by identity.
        localInputs.value = [...localInputs.value];
    } catch (e) {
        console.warn("history-contents pagination failed", e);
    }
}

function onLoadMore({
    name,
    src,
    offset,
    limit,
    search,
}: {
    name: string;
    src: string;
    offset: number;
    limit: number;
    search?: string;
}) {
    fetchStepOptions(name, src, { offset, limit, search });
}

// Coalesce per-keystroke searches into one backend round trip.
const onSearchChange = debounce(
    ({ name, src, query, limit }: { name: string; src: string; query: string; limit?: number }) => {
        fetchStepOptions(name, src, { offset: 0, limit: limit || DEFAULT_OPTIONS_PAGE_SIZE, search: query });
    },
    400,
);

watch(
    () => props.validationScrollTo,
    () => {
        if (props.validationScrollTo.length > 0) {
            expanded.value = true;
        }
    },
);

watch(
    () => props.model.inputs,
    () => {
        localInputs.value = buildLocalInputs();
    },
);

onBeforeUnmount(() => {
    onSearchChange.cancel();
});
</script>
