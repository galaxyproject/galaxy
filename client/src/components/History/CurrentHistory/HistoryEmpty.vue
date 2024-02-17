<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useEventBus } from "@vueuse/core";
import { BAlert } from "bootstrap-vue";

import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import localize from "@/utils/localization";

library.add(faInfoCircle);

const { emit } = useEventBus<string>("open-tool-section");

const props = withDefaults(
    defineProps<{
        message?: string;
        writable?: boolean;
    }>(),
    {
        message: "This history is empty.",
        writable: true,
    }
);

const { openGlobalUploadModal } = useGlobalUploadModal();
function clickDataLink() {
    emit("getext");
}
</script>

<template>
    <BAlert show>
        <h4 id="empty-history-message" class="mb-1">
            <FontAwesomeIcon :icon="faInfoCircle" />
            <span>{{ localize(message) }}</span>
        </h4>

        <p v-if="props.writable">
            <a v-localize href="#" @click.prevent="openGlobalUploadModal">You can load your own data</a>
            <span v-localize>or</span>
            <a v-localize href="#" @click.prevent="clickDataLink">get data from an external source</a>.
        </p>
    </BAlert>
</template>
