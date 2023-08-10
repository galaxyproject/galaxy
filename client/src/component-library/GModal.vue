<script lang="ts" setup>
import { BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

interface Props {
    value?: boolean;
    visible?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: boolean): void;
}>();

const modalRef = ref();

const model = computed({
    get: () => props.value ?? props.visible ?? false,
    set: (value) => {
        emit("input", value);
    },
});

function hide() {
    modalRef.value.hide();
}

function show() {
    modalRef.value.show();
}

function toggle() {
    modalRef.value.toggle();
}

defineExpose({
    hide,
    show,
    toggle,
});
</script>

<template>
    <BModal ref="modalRef" v-model="model" v-bind="$attrs" v-on="$listeners">
        <template v-for="(_, slot) of $scopedSlots" v-slot:[slot]="scope">
            <slot :name="slot" v-bind="scope" />
        </template>
    </BModal>
</template>
