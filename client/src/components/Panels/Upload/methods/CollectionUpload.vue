<script setup lang="ts">
import type { UploadMethodConfig } from "../types";

import GTip from "@/components/BaseComponents/GTip.vue";

interface Props {
    method: UploadMethodConfig;
}

defineProps<Props>();
</script>

<template>
    <div class="collection-upload">
        <GTip
            :tips="'Galaxy supports various collection types, including list, paired, and nested collections. To learn more about collections and how to structure your files for upload, please refer to the [Galaxy Training Network](https://training.galaxyproject.org/training-material/topics/galaxy-interface/tutorials/collections/tutorial.html).'"
            class="mb-4" />

        <div class="text-center m-4">TODO</div>
    </div>
</template>
