<script setup>
import { computed, onMounted, inject } from "vue";

// Needs to resolve a dataset.  This should be a composable, usesDataset

const props = defineProps({
    options: {
        type: Object,
        required: true,
    },
});

console.debug("loaded");

onMounted(() => {
    console.debug("All done, mounted");
});
</script>

<template>
    <div>
        Tabular display.
        <div v-if="props.options">
            <pre>{{ props.options }}</pre>
        </div>
        <!-- 
            <script type="text/javascript">
                config.addInitialization(function(galaxy) {
                    var dataset = ${ h.dumps( trans.security.encode_dict_ids( dataset.to_dict() ) )};
                    var firstChunk = ${chunk};
                    var datasetConfig = Object.assign(dataset, { first_data_chunk: firstChunk })
                    window.bundleEntries.createNewTabularDatasetChunkedView({
                        dataset_config : datasetConfig,
                        parent_elt : document.body
                    });
                });
            </script>
        -->
    </div>
</template>

<style lang="scss" scoped></style>
