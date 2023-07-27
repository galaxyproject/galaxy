<script setup>
import Popper from "@/components/Popper/Popper.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSearch } from "@fortawesome/free-solid-svg-icons";

library.add(faSearch);

const props = defineProps({
    extensionDetails: Object,
});
</script>

<template>
    <Popper placement="bottom" mode="light">
        <template v-slot:reference>
            <FontAwesomeIcon icon="fa-search" />
        </template>
        <div class="p-2">
            <div v-if="extensionDetails">
                {{ extensionDetails.description }}
                <span v-if="extensionDetails.description_url">
                    &nbsp;(<a :href="extensionDetails.description_url" target="_blank">read more</a>)
                </span>
            </div>
            <div v-else>There is no description available for this file extension.</div>
        </div>
    </Popper>
</template>
