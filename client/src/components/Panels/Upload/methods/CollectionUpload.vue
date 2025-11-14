<script setup lang="ts">
import { BAlert } from "bootstrap-vue";

import ExternalLink from "@/components/ExternalLink.vue";
</script>

<template>
    <div class="collection-upload">
        <BAlert show variant="info" class="mb-4">
            <p>
                Collections group multiple datasets together for easier batch processing. All files will be uploaded as
                a single collection item.
            </p>
            <p>
                Galaxy supports various collection types, including list, paired, and nested collections. To learn more
                about collections and how to structure your files for upload, please refer to the
                <ExternalLink
                    href="https://training.galaxyproject.org/training-material/topics/galaxy-interface/tutorials/collections/tutorial.html">
                    Galaxy Training Network
                </ExternalLink>
            </p>
        </BAlert>

        <div class="text-center m-4">TODO</div>
    </div>
</template>
