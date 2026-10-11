<template>
    <div :step-label="model.step_label">
        <FormCard v-model:expanded="expanded" :title="model.fixed_title" :icon="icon" :collapsible="true">
            <template v-slot:title>
                <span v-if="credentialInfo?.toolId" v-g-tooltip.hover title="Uses credentials">
                    <FontAwesomeIcon :icon="faKey" fixed-width />
                </span>
            </template>
            <template v-slot:body>
                <ToolCredentials
                    v-if="credentialInfo?.toolId"
                    :tool-id="credentialInfo.toolId"
                    :tool-version="credentialInfo.toolVersion" />
                <FormMessage :message="errorText" variant="danger" :persistent="true" />
                <FormDisplay
                    :inputs="modelInputs"
                    :sustain-repeats="true"
                    :sustain-conditionals="true"
                    :replace-params="replaceParams"
                    :validation-scroll-to="formValidationScrollTo"
                    collapsed-enable-text="Edit"
                    :collapsed-enable-icon="faEdit"
                    collapsed-disable-text="Undo"
                    :collapsed-disable-icon="faUndo"
                    @load-more="onLoadMore"
                    @search-change="onSearchChange"
                    @onChange="onChange"
                    @onValidation="onValidation" />
            </template>
        </FormCard>
    </div>
</template>

<script setup lang="ts">
import { faEdit, faKey, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { debounce } from "lodash";
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, ref, watch } from "vue";

import type { FormData, FormInputNode } from "@/components/Form/composables/useFormState";
import type { DataOption } from "@/components/Form/Elements/FormData/types";
import { findInputByDottedName, visitInputs } from "@/components/Form/utilities";
import WorkflowIcons from "@/components/Workflow/icons";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";

import { getTool } from "./services";

import FormCard from "@/components/Form/FormCard.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import FormMessage from "@/components/Form/FormMessage.vue";
import ToolCredentials from "@/components/Tool/ToolCredentials.vue";

type StepInput = FormInputNode & Record<string, any>;
type OptionsPagination = Record<string, Record<string, { offset: number; limit?: number; search?: string }>>;

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
     * History used to build the tool form
     * @default null
     */
    historyId?: string | null;
    /**
     * Values of linked workflow parameters and data steps, keyed by input name
     * @default null
     */
    replaceParams?: Record<string, unknown> | null;
}

const props = withDefaults(defineProps<Props>(), {
    historyId: null,
    replaceParams: null,
});

const emit = defineEmits<{
    (e: "onChange", index: string, data: FormData): void;
    (e: "onValidation", index: string, validation: [string, string] | null): void;
}>();

const { lastUpdateTime } = storeToRefs(useHistoryItemsStore());

const expanded = ref<boolean>(props.model.expanded);
const errorText = ref<string>();
const modelInputs = ref<StepInput[]>(props.model.inputs);
// Not render state: only read when requesting the tool model.
let modelData: FormData = {};
let modelIndex: Record<string, StepInput> = {};

const credentialInfo = computed(() => {
    if (!props.model.credentials?.length) {
        return null;
    }

    return {
        toolId: props.model.id,
        toolVersion: props.model.version,
        toolCredentials: props.model.credentials,
    };
});

const icon = computed(() => (WorkflowIcons as Record<string, string>)[props.model.step_type]);

const historyStatusKey = computed(() => `${props.historyId}_${lastUpdateTime.value}`);

// FormDisplay takes null rather than an empty array.
const formValidationScrollTo = computed(() =>
    props.validationScrollTo.length === 2 ? props.validationScrollTo : null,
);

function onCreateIndex() {
    modelIndex = {};
    visitInputs(modelInputs.value, (input: StepInput, name: string) => {
        modelIndex[name] = input;
    });
}

function onHistoryChange() {
    onUpdate();
}

function onChange(data: FormData, refreshRequest?: boolean) {
    modelData = data;
    if (refreshRequest) {
        onUpdate();
    }
    emit("onChange", props.model.index, data);
}

function onUpdate() {
    getTool(props.model.id, props.model.version, modelData, props.historyId).then(
        (newModel) => {
            onCreateIndex();
            visitInputs(newModel.inputs, (newInput: StepInput, name: string) => {
                const input = modelIndex[name]!;
                input.options = newInput.options;
                input.textable = newInput.textable;
            });
            modelInputs.value = JSON.parse(JSON.stringify(modelInputs.value));
        },
        (error) => {
            errorText.value = error;
        },
    );
}

function onValidation(validation: [string, string] | null) {
    emit("onValidation", props.model.index, validation);
}

/**
 * Lazy-load the next page of options for a paginated data parameter
 * dropdown. Mirrors ``ToolForm.vue:onLoadMore`` but routes through
 * ``getTool`` since the workflow run form fetches per-step tool data
 * via ``Workflow/Run/services.js``. Append-merges the new options into
 * the matching parameter so already-loaded items stay visible.
 */
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
    const spec: { offset: number; limit: number; search?: string } = { offset, limit };
    if (search) {
        spec.search = search;
    }
    const optionsPagination: OptionsPagination = { [name]: { [src]: spec } };
    getTool(props.model.id, props.model.version, modelData, props.historyId, optionsPagination).then(
        (newModel) => mergeFetchedOptions(name, src, newModel),
        (error) => {
            errorText.value = error;
        },
    );
}

/**
 * Refetch the parameter's options filtered by the typed search query.
 * The fetched matches are merged into the loaded options so the list
 * cannot become empty and unmount the focused multiselect mid-typing;
 * FormSelect's client-side filter still narrows the visible union.
 * Debounced so rapid typing coalesces into a single backend round trip.
 */
const onSearchChange = debounce(
    ({ name, src, query, limit }: { name: string; src: string; query: string; limit?: number }) => {
        const spec: { offset: number; limit?: number; search?: string } = { offset: 0, limit };
        if (query) {
            spec.search = query;
        }
        const optionsPagination: OptionsPagination = { [name]: { [src]: spec } };
        getTool(props.model.id, props.model.version, modelData, props.historyId, optionsPagination).then(
            (newModel) => mergeFetchedOptions(name, src, newModel),
            (error) => {
                errorText.value = error;
            },
        );
    },
    400,
);

function mergeFetchedOptions(name: string, src: string, newModel: { inputs: StepInput[] }) {
    const target = findInputByDottedName(modelInputs.value, name) as StepInput | null;
    const incoming = findInputByDottedName(newModel.inputs, name) as StepInput | null;
    if (!target || !incoming) {
        return;
    }
    const existing = (target.options as Record<string, DataOption[]> | undefined)?.[src] || [];
    const newOptions = (incoming.options as Record<string, DataOption[]> | undefined)?.[src] || [];
    const seen = new Set(existing.map((option) => `${option.id}_${option.src}`));
    const merged = existing.concat(
        newOptions.filter((option) => {
            const key = `${option.id}_${option.src}`;
            if (seen.has(key)) {
                return false;
            }
            seen.add(key);
            return true;
        }),
    );
    target.options = { ...target.options, [src]: merged };
    if (incoming.options_meta && incoming.options_meta[src]) {
        target.options_meta = {
            ...(target.options_meta || {}),
            [src]: incoming.options_meta[src],
        };
    }
    // FormDisplay only syncs server-owned attributes when the inputs prop changes by identity.
    modelInputs.value = [...modelInputs.value];
}

watch(
    () => props.validationScrollTo,
    () => {
        if (props.validationScrollTo.length > 0) {
            expanded.value = true;
        }
    },
);

watch(historyStatusKey, () => {
    onHistoryChange();
});

onBeforeUnmount(() => {
    onSearchChange.cancel();
});
</script>
