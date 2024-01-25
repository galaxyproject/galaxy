<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDoubleLeft, faAngleLeft } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

library.add(faAngleDoubleLeft, faAngleLeft);

interface Props {
    historyName: string;
    selectedCollections: object[];
}

const props = defineProps<Props>();

const emit = defineEmits(["update:selected-collections"]);

const previousName = computed(() => {
    const length = props.selectedCollections.length;

    if (length > 1) {
        const last = props.selectedCollections[length - 2] as { name: string; element_identifier: string };
        return last?.name || last?.element_identifier;
    }

    return null;
});

function back() {
    const newList = props.selectedCollections.slice(0, -1);
    emit("update:selected-collections", newList);
}

function close() {
    emit("update:selected-collections", []);
}
</script>

<template>
    <div class="mx-1 mt-1">
        <BButton
            v-b-tooltip:hover="historyName"
            size="sm"
            class="text-left text-decoration-none overflow-hidden text-nowrap w-100"
            style="text-overflow: ellipsis"
            variant="link"
            @click="close">
            <FontAwesomeIcon :icon="faAngleDoubleLeft" class="mr-1" data-description="back to history" fixed-width />
            <span> History: {{ historyName }} </span>
        </BButton>

        <BButton v-if="previousName" size="sm" class="text-decoration-none" variant="link" @click="back">
            <FontAwesomeIcon :icon="faAngleLeft" class="mr-1" fixed-width />
            <span>{{ previousName }}</span>
        </BButton>
    </div>
</template>
