<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { computed, ref } from "vue";

import FormText from "@/components/Form/Elements/FormText.vue";

interface Props {
    value?: string;
    id?: string;
    type?: string;
    area?: boolean;
    multiple?: boolean;
    readonly?: boolean;
    placeholder?: string;
    datalist?: { value: string; label: string }[];
}

const props = withDefaults(defineProps<Props>(), {
    value: "",
    id: "",
    type: "text",
    area: false,
    multiple: false,
    readonly: false,
    placeholder: "",
    datalist: () => [],
});

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const status = ref(false);

const currentValue = computed({
    get() {
        return props.value;
    },
    set(val) {
        emit("input", val);
    },
});
const currentStatus = computed({
    get() {
        return status.value || props.value !== null;
    },
    set(val) {
        status.value = Boolean(val);

        currentValue.value = "";
    },
});
</script>

<template>
    <div>
        <BFormCheckbox v-model="currentStatus" class="ui-switch" switch>
            Set value for this optional select field?
        </BFormCheckbox>

        <FormText
            v-if="currentStatus"
            :id="id"
            v-model="currentValue"
            :readonly="readonly"
            :area="area"
            :placeholder="placeholder"
            :multiple="multiple"
            :datalist="datalist"
            :type="type" />
    </div>
</template>
