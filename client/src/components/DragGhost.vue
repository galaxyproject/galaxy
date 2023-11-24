<script setup>
import { computed } from "vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faPaperPlane } from "@fortawesome/free-solid-svg-icons";
import { useEventStore } from "stores/eventStore";
import TextShort from "@/components/Common/TextShort.vue";

library.add(faPaperPlane);

const eventStore = useEventStore();

const name = computed(() => {
    const dragData = eventStore.getDragData();
    return dragData?.name ?? "Draggable";
});
</script>

<template>
    <span id="drag-ghost" class="py-2 px-3 rounded">
        <font-awesome-icon icon="paper-plane" class="mr-1" />
        <text-short class="font-weight-bold" :text="name" />
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
