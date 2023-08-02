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
        <template v-slot:modal-header>
            <slot name="modal-header"></slot>
        </template>

        <template v-slot:modal-title>
            <slot name="modal-title"></slot>
        </template>

        <slot></slot>

        <template v-slot:modal-body>
            <slot name="modal-body"></slot>
        </template>

        <template v-slot:modal-footer>
            <slot name="modal-footer"></slot>
        </template>
    </BModal>
</template>
