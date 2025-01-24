<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChartBar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import localize from "@/utils/localization";

import type { DataValuePoint } from "./Charts";

interface Props {
    data: DataValuePoint;
}

const props = defineProps<Props>();

library.add(faChartBar);

const label = computed(() => props.data.label);
const viewDetailsIcon = computed(() => "chart-bar");

const emit = defineEmits<{
    (e: "view-item", itemId: string): void;
}>();

function onViewItem() {
    emit("view-item", props.data.id);
}
</script>
<template>
    <div class="selected-item-info">
        <div class="h-md mx-2">
            <b>{{ label }}</b>
        </div>

        <div class="my-2">
            <BButton
                variant="outline-primary"
                size="sm"
                class="mx-2"
                :title="localize(`Go to the details of this storage location`)"
                @click="onViewItem">
                <FontAwesomeIcon :icon="viewDetailsIcon" />
            </BButton>
        </div>
    </div>
</template>
