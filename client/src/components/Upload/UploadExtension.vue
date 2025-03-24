<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { findExtension } from "./utils";

import Popper from "@/components/Popper/Popper.vue";

library.add(faSearch);

const props = defineProps({
    extension: {
        type: String,
        default: null,
    },
    listExtensions: {
        type: Array,
        default: null,
    },
});

const details = computed(() => findExtension(props.listExtensions, props.extension));
</script>

<template>
    <Popper placement="bottom" mode="light">
        <template v-slot:reference>
            <FontAwesomeIcon icon="fa-search" />
        </template>
        <div class="p-2">
            <div v-if="details && details.description">
            {{ details.description }}
            <div v-if="details.descriptionUrl">
                &nbsp;(<a :href="details.descriptionUrl" target="_blank">了解更多</a>)
            </div>
            </div>
            <div v-else>此文件扩展名没有可用的描述信息。</div>
        </div>
    </Popper>
</template>
