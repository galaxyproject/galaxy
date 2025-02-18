<script setup lang="ts">
import { BCol, BFormInput, BFormTextarea, BRow } from "bootstrap-vue";
import { computed } from "vue";

import type { FormParameterTypeMap } from "../parameterTypes";

interface Props {
    value?: FormParameterTypeMap["text"];
    id?: string;
    type?: "text" | "password";
    /** <textarea> instead of <input> element */
    area?: boolean;
    /** Allow multiple entries to be created */
    multiple?: boolean;
    readonly?: boolean;
    placeholder?: string;
    optional?: boolean;
    showState?: boolean;
    color?: string;
    /** Refers to an optional custom css class name */
    cls?: string;
    /** Display list of suggestions in autocomplete dialog */
    datalist?: { label: string; value: string }[];
}

const props = withDefaults(defineProps<Props>(), {
    value: "",
    id: "",
    type: "text",
    area: false,
    multiple: false,
    readonly: false,
    placeholder: "",
    optional: true,
    showState: false,
    color: undefined,
    cls: undefined,
    datalist: undefined,
});
const emit = defineEmits(["input"]);

const acceptedTypes = computed(() => (["text", "password"].includes(props.type) ? props.type : "text"));

const currentValue = computed({
    get() {
        const v = props.value ?? "";
        if (Array.isArray(v)) {
            if (v.length === 0) {
                return "";
            }
            return props.multiple ? v.reduce((str_value, v) => str_value + String(v) + "\n", "") : String(v[0]);
        }
        return String(v);
    },
    set(newVal: string) {
        emit("input", newVal);
    },
});

const inputArea = computed(() => props.area || props.multiple);

const style = computed(() => (props.color ? { color: props.color, "border-color": props.color } : null));
</script>
<template>
    <BRow align-v="center">
        <BCol>
            <BFormTextarea
                v-if="inputArea"
                :id="id"
                v-model="currentValue"
                :class="['ui-text-area', cls]"
                :readonly="readonly"
                :placeholder="placeholder"
                :style="style" />
            <BFormInput
                v-else
                :id="id"
                v-model="currentValue"
                :class="['ui-input', cls]"
                :readonly="readonly"
                :placeholder="placeholder"
                :state="showState ? (!currentValue ? (optional ? null : false) : true) : null"
                :style="style"
                :type="acceptedTypes"
                :list="`${id}-datalist`" />
            <datalist v-if="datalist && !inputArea" :id="`${id}-datalist`">
                <option v-for="data in datalist" :key="data.value" :label="data.label" :value="data.value" />
            </datalist>
        </BCol>
    </BRow>
</template>

<style scoped>
.ui-input-linked {
    border-left-width: 0.5rem;
}
</style>
