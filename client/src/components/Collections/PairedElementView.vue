<script setup lang="ts">
import { faArrowLeft, faArrowRight, faUnlink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { ref, watch } from "vue";

import type { HDASummary } from "@/api";
import localize from "@/utils/localization";

import ClickToEdit from "@/components/Collections/common/ClickToEdit.vue";

interface Props {
    pair: {
        name: string;
        forward: HDASummary;
        reverse: HDASummary;
    };
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (event: "onPairRename", name: string): void;
    (event: "onUnpair"): void;
}>();

const elementName = ref(props.pair.name);

watch(elementName, () => {
    emit("onPairRename", elementName.value);
});
</script>

<template>
    <li class="d-flex align-items-center justify-content-between">
        <div class="dataset paired w-100">
            <span class="forward-dataset-name flex-column">
                {{ pair.forward.name }}
                <FontAwesomeIcon :icon="faArrowRight" fixed-width />
            </span>

            <span class="pair-name-column flex-column">
                <span class="pair-name">
                    <ClickToEdit v-model="elementName" :title="localize('重命名')" />
                </span>
            </span>

            <span class="reverse-dataset-name flex-column">
                <FontAwesomeIcon :icon="faArrowLeft" fixed-width />
                {{ pair.reverse.name }}
            </span>
        </div>

        <BButton class="unpair-btn" variant="link" @click="emit('onUnpair')">
            <FontAwesomeIcon :icon="faUnlink" :title="localize('取消配对')" />
        </BButton>
    </li>
</template>
