<script setup>
import { BButton } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCloudUploadAlt } from "@fortawesome/free-solid-svg-icons";
library.add(faCloudUploadAlt);

const props = defineProps({
    title: { type: String, required: true },
});

const emit = defineEmits(["onExportToFileSource"]);
</script>

<template>
    <div>
        <b-button :title="props.title" @click="() => emit('onExportToFileSource')">
            <font-awesome-icon icon="cloud-upload-alt" />
        </b-button>
    </div>
</template>
