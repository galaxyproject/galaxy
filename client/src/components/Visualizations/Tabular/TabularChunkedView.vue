<script setup>
import { computed, onMounted } from "vue";

import useDataset from "@/composables/useDataset";

console.debug(useDataset)
// Needs to resolve a dataset.  This should be a composable, useDataset

const props = defineProps({
    options: {
        type: Object,
        required: true,
    },
});

console.debug("loaded");

const dataset = useDataset(props.options.datasetId);

const headers = computed(() => {
    return props.options.headers;
});

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
        <table>
            <tr>
                <th>Column 1</th>
                <th>Column 2</th>
            </tr>
            <tr>
                <td>Row 1, Column 1</td>
                <td>Row 1, Column 2</td>
            </tr>
            <tr>
                <td>Row 2, Column 1</td>
                <td>Row 2, Column 2</td>
            </tr>
        </table>
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
