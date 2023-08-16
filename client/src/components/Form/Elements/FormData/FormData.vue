<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import { faExclamation, faLink, faUnlink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox, BFormRadio, BFormRadioGroup } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { DataOption, DataValue } from "./types";
import { BATCH, VARIANTS } from "./variants";

import FormDataSelect from "./FormDataSelect.vue";

library.add(faCopy, faExclamation, faFile, faFolder, faLink, faUnlink);

interface DataOptions {
    hda: Array<DataOption>;
    hdca: Array<DataOption>;
}

const props = withDefaults(
    defineProps<{
        multiple?: boolean;
        optional?: boolean;
        options: DataOptions;
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
        console.log("in", props.value.values);
        return props.value.values;
    },
    set: (val) => {
        console.log("out", val);
        $emit("input", val);
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
            <BFormRadioGroup v-model="currentField" buttons class="align-self-start mr-2">
                <BFormRadio v-for="(v, index) in variant" :key="index" :value="index">
                    <FontAwesomeIcon :icon="['far', v.icon]" />
                </BFormRadio>
            </BFormRadioGroup>
            <FormDataSelect
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
