<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUnlink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { onMounted, ref, watch } from "vue";

import localize from "@/utils/localization";

import ClickToEdit from "@/components/Collections/common/ClickToEdit.vue";

library.add(faUnlink);

interface Props {
    // TODO: Define the type of the pair prop
    pair: {
        name: string;
        forward: { name: string };
        reverse: { name: string };
    };
    unlinkFn: () => void;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (event: "onPairRename", name: string): void;
}>();

const name = ref("");

watch(
    () => props.pair,
    () => {
        name.value = props.pair.name;
    }
);

watch(name, () => {
    emit("onPairRename", name.value);
});

onMounted(() => {
    name.value = props.pair.name;
});
</script>

<template>
    <div>
        <li class="dataset paired">
            <span class="forward-dataset-name flex-column">
                {{ pair.forward.name }}
            </span>

            <span class="pair-name-column flex-column">
                <span class="pair-name">
                    <ClickToEdit v-model="name" :title="localize('Click to rename')" />
                </span>
            </span>

            <span class="reverse-dataset-name flex-column">
                {{ pair.reverse.name }}
            </span>
        </li>

        <button class="unpair-btn" @click="unlinkFn">
            <FontAwesomeIcon :icon="faUnlink" :title="localize('Unpair')" />
        </button>
    </div>
</template>
