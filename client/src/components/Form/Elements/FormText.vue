<script setup lang="ts">
import { BCol, BFormInput, BFormTextarea, BRow } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    id?: string;
    cls?: string;
    type?: string;
    color?: string;
    area?: boolean;
    multiple?: boolean;
    readonly?: boolean;
    placeholder?: string;
    value?: string | string[];
    datalist?: { value: string; label: string }[];
}

const props = withDefaults(defineProps<Props>(), {
    id: "",
    cls: "",
    type: "text",
    color: "",
    area: false,
    multiple: false,
    readonly: false,
    placeholder: "",
    value: "",
    datalist: () => [],
});

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const acceptedTypes = computed(() => {
    return ["text", "password"].includes(props.type) ? props.type : "text";
});
const inputArea = computed(() => {
    return props.area || props.multiple;
});
const style = computed(() => {
    return props.color
        ? {
              color: props.color,
              "border-color": props.color,
          }
        : null;
});
const currentValue = computed({
    get() {
        const v = props.value ?? "";

        if (Array.isArray(v)) {
            if (v.length === 0) {
                return "";
            }

            return props.multiple && Array.isArray(props.value)
                ? props.value.reduce((str_value: string, v: string) => str_value + String(v) + "\n", "")
                : String(props.value[0]);
        }

        return String(v);
    },
    set(newVal: string) {
        if (newVal !== props.value) {
            emit("input", newVal);
        }
    },
});
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
