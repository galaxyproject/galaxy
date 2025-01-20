<script setup lang="ts">
import { faCaretDown, faCaretUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCollapse, BTooltip } from "bootstrap-vue";
import { computed } from "vue";

import { orList } from "@/utils/strings";

const props = defineProps<{
    extensions: string[];
    formatsButtonId: string;
    formatsVisible: boolean;
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
    <div>
        <BButton
            :id="props.formatsButtonId"
            class="ui-link d-flex align-items-center text-nowrap flex-gapx-1"
            @click="localFormatsVisible = !localFormatsVisible">
            <span v-localize>accepted formats</span>
            <FontAwesomeIcon v-if="formatsVisible" :icon="faCaretUp" />
            <FontAwesomeIcon v-else :icon="faCaretDown" />
        </BButton>
        <BCollapse v-model="localFormatsVisible">
            <ul class="pl-3 m-0">
                <li v-for="extension in props.extensions" :key="extension">{{ extension }}</li>
            </ul>
        </BCollapse>
        <BTooltip :target="props.formatsButtonId" noninteractive placement="bottom" triggers="hover">
            <div class="form-data-props.extensions-tooltip">
                <span>{{ orList([...props.extensions]) }}</span>
            </div>
        </BTooltip>
    </div>
</template>
