<script setup lang="ts">
import { faCaretDown, faCaretUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BPopover } from "bootstrap-vue";
import { computed } from "vue";

import { orList } from "@/utils/strings";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCollapse from "@/components/BaseComponents/GCollapse.vue";

const props = defineProps<{
    extensions: string[];
    formatsButtonId: string;
    formatsVisible: boolean;
    popover?: boolean;
    minimal?: boolean;
}>();

const emit = defineEmits<{
    (e: "update:formats-visible", formatsVisible: boolean): void;
}>();

/** Computed toggle that handles opening and closing the modal */
const localFormatsVisible = computed({
    get: () => props.formatsVisible,
    set: (value: boolean) => {
        // emit("update:show-modal", value);
        emit("update:formats-visible", value);
    },
});
</script>
<template>
    <div v-if="props.minimal && props.extensions.length <= 2" class="font-italic font-weight-normal">
        <span v-localize>accepted formats:</span>
        <span>{{ orList([...props.extensions]) }}</span>
    </div>
    <div v-else>
        <GButton
            :id="props.formatsButtonId"
            v-g-tooltip.hover.bottom="!formatsVisible ? orList([...props.extensions]) : ''"
            size="small"
            color="blue"
            transparent
            inline
            v-model:pressed="localFormatsVisible">
            <span v-localize>accepted formats</span>
            <FontAwesomeIcon v-if="formatsVisible" :icon="faCaretUp" />
            <FontAwesomeIcon v-else :icon="faCaretDown" />
        </GButton>
        <BPopover
            v-if="props.popover"
            v-model="localFormatsVisible"
            :target="props.formatsButtonId"
            v-model:show="localFormatsVisible"
            placement="bottom">
            <ul class="pl-3 m-0">
                <li v-for="extension in props.extensions" :key="extension">{{ extension }}</li>
            </ul>
        </BPopover>
        <GCollapse v-else :visible="localFormatsVisible">
            <ul class="pl-3 m-0">
                <li v-for="extension in props.extensions" :key="extension">{{ extension }}</li>
            </ul>
        </GCollapse>
    </div>
</template>
