<script setup lang="ts">
import { useEventBus } from "@vueuse/core";
import { BAlert } from "bootstrap-vue";

import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import localize from "@/utils/localization";

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
        <h4 class="mb-1">
            <i class="fa fa-info-circle empty-message"></i>
            <span>{{ localize(message) }}</span>
        </h4>

        <p v-if="props.writable">
            <a v-localize href="#" @click.prevent="openGlobalUploadModal">You can load your own data</a>
            <span v-localize>or</span>
            <a v-localize href="#" @click.prevent="clickDataLink">get data from an external source</a>.
        </p>
    </BAlert>
</template>
