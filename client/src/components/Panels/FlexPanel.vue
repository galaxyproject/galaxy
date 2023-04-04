<script setup>
import { ref } from "vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faChevronLeft, faChevronRight } from "@fortawesome/free-solid-svg-icons";

library.add({
    faChevronLeft,
    faChevronRight,
});

const show = ref(true);

function toggle() {
    show.value = !show.value;
}
</script>

<template>
    <div class="d-flex">
        <div class="d-flex flex-column">
            <slot v-if="show" />
            <div v-else class="flex-fill" />
            <div class="align-self-end px-2 py-1" @click="toggle">
                <icon v-if="show" icon="chevron-right" />
                <icon v-else icon="chevron-left" />
            </div>
        </div>
    </div>
</template>
