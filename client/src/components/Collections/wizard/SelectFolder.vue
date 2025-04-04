<script setup lang="ts">
import { BFormGroup, BLink } from "bootstrap-vue";
import { ref, watch } from "vue";

import FilesInput from "@/components/FilesDialog/FilesInput.vue";

interface Props {
    ftpUploadSite?: string;
}

defineProps<Props>();

const remoteUri = ref<string>("");

const emit = defineEmits(["onChange", "onFtp"]);

watch(remoteUri, (newValue: string) => {
    emit("onChange", newValue);
});
</script>

<template>
    <div>
        <BFormGroup
            id="fieldset-directory"
            label-for="directory"
            :description="`Select a 'remote files' directory to import from.`"
            class="mt-3">
            <FilesInput id="directory" v-model="remoteUri" mode="directory" :require-writable="false" />
        </BFormGroup>
        <div v-if="ftpUploadSite">
            Alternatively, <BLink @click="emit('onFtp')">click here to load your Galaxy FTP directory contents</BLink>.
        </div>
    </div>
</template>
