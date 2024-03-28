<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPaperPlane } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { useEventStore } from "stores/eventStore";
import { computed } from "vue";

import TextShort from "@/components/Common/TextShort.vue";

library.add(faPaperPlane);

const eventStore = useEventStore();
const { multipleDragData } = storeToRefs(eventStore);

const name = computed(() => {
    const dragData = eventStore.getDragData();
    if (multipleDragData.value) {
        const count = Object.keys(dragData).length;
        return `${count} items`;
    }
    return dragData?.name ?? "Draggable";
});
</script>

<template>
    <span id="drag-ghost" class="py-2 px-3 rounded">
        <FontAwesomeIcon :icon="faPaperPlane" class="mr-1" />
        <TextShort class="font-weight-bold" :text="name" />
    </span>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

#drag-ghost {
    background: $brand-light;
    color: $brand-dark;
    position: absolute;
    top: -9999px;
}
</style>
