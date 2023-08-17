<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import { faExclamation, faLink, faUnlink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox, BFormRadio, BFormRadioGroup } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { DataOption, DataValue } from "./types";
import { BATCH, SOURCE, VARIANTS } from "./variants";

import FormSelect from "@/components/Form/Elements/FormSelect.vue";

library.add(faCopy, faExclamation, faFile, faFolder, faLink, faUnlink);

const props = withDefaults(
    defineProps<{
        multiple?: boolean;
        optional?: boolean;
        options: Record<string, Array<DataOption>>;
        value?: DataValue;
        extensions?: Array<string>;
        type?: string;
        flavor?: string;
        tag?: string;
    }>(),
    {
        multiple: false,
        optional: false,
        value: null,
        extensions: () => [],
        type: "data",
        flavor: null,
        tag: null,
    }
);

const $emit = defineEmits(["input"]);

const currentBatch = ref(true);

const currentField = ref(0);

const currentValue = computed({
    get: () => {
        const value: Array<DataOption> = [];
        if (props.value) {
            props.value.values.forEach((v) => {
                const sourceOptions = props.options[v.src];
                if (sourceOptions) {
                    const foundEntry = sourceOptions.find((entry) => entry.id === v.id);
                    if (foundEntry) {
                        value.push(foundEntry);
                    }
                }
            });
            return value;
        } else {
            return null;
        }
    },
    set: (val) => {
        const batchMode = currentVariant.value && currentVariant.value.batch;
        if (val) {
            const values = Array.isArray(val) ? val : [val];
            $emit("input", {
                batch: batchMode !== BATCH.DISABLED,
                product: batchMode === BATCH.ENABLED && !currentBatch.value,
                values: values.map((entry) => ({
                    id: entry.id,
                    src: entry.src,
                    map_over_type: entry.map_over_type,
                })),
            });
        } else {
            $emit("input", null);
        }
    },
});

const currentVariant = computed(() => {
    if (variant.value && currentField.value < variant.value.length) {
        return variant.value[currentField.value];
    } else {
        return null;
    }
});

const variant = computed(() => {
    const flavorKey = props.flavor ? `${props.flavor}_` : "";
    const multipleKey = props.multiple ? `_${props.multiple}` : "";
    const variantKey = `${flavorKey}${props.type}${multipleKey}`;
    return VARIANTS[variantKey];
});
</script>

<template>
    <div>
        <div class="d-flex">
            <BFormRadioGroup v-if="variant.length > 1" v-model="currentField" buttons class="align-self-start mr-2">
                <BFormRadio v-for="(v, index) in variant" :key="index" :value="index">
                    <FontAwesomeIcon :icon="['far', v.icon]" />
                </BFormRadio>
            </BFormRadioGroup>
            <FormSelect
                v-if="currentVariant"
                v-model="currentValue"
                class="w-100"
                :multiple="currentVariant.multiple"
                :optional="optional"
                :options="options[currentVariant.src]" />
        </div>
        <div v-if="currentVariant.batch !== BATCH.DISABLED">
            <BFormCheckbox
                v-if="currentVariant.batch === BATCH.ENABLED"
                v-model="currentBatch"
                class="no-highlight my-2"
                switch>
                <div v-if="currentBatch">
                    <FontAwesomeIcon icon="fa-link" />
                    <b v-localize class="mr-1">Linked:</b>
                    <span v-localize>Datasets will be run in matched order with other datasets.</span>
                </div>
                <span v-else>
                    <FontAwesomeIcon icon="fa-unlink" />
                    <b v-localize class="mr-1">Unlinked:</b>
                    <span v-localize>Dataset will be run against *all* other datasets.</span>
                </span>
            </BFormCheckbox>
            <div class="text-info my-2">
                <FontAwesomeIcon icon="fa-exclamation" />
                <span v-localize class="ml-1">
                    This is a batch mode input field. Individual jobs will be triggered for each dataset.
                </span>
            </div>
        </div>
    </div>
</template>
