<script setup lang="ts">
import { type HDADetailed } from "@/api";
import { withPrefix } from "@/utils/redirect";
import { bytesToString } from "@/utils/utils";

import DatasetHashes from "@/components/DatasetInformation/DatasetHashes.vue";
import DatasetSources from "@/components/DatasetInformation/DatasetSources.vue";
import DecodedId from "@/components/DecodedId.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    dataset: HDADetailed;
}

defineProps<Props>();
</script>

<template>
    <div v-if="dataset">
        <h2 class="h-md">Dataset Information</h2>

        <table id="dataset-details" class="tabletip info_data_table">
            <tbody>
                <tr>
                    <td>Number</td>

                    <td id="number">
                        {{ dataset.hid }}
                    </td>
                </tr>

                <tr>
                    <td>Name</td>

                    <td id="name">
                        {{ dataset.name }}
                    </td>
                </tr>

                <tr>
                    <td>Created</td>

                    <td v-if="dataset.create_time" id="created">
                        <UtcDate :date="dataset.create_time" mode="pretty" />
                    </td>
                </tr>

                <tr>
                    <td>Filesize</td>

                    <td id="file-size" v-html="bytesToString(dataset.file_size, false)" />
                </tr>

                <tr>
                    <td>Dbkey</td>

                    <td id="dbkey">
                        {{ dataset.metadata_dbkey }}
                    </td>
                </tr>

                <tr>
                    <td>Format</td>

                    <td id="format">
                        {{ dataset.file_ext }}
                    </td>
                </tr>

                <tr>
                    <td>File contents</td>

                    <td id="file-contents">
                        <a :href="withPrefix(dataset.download_url)">contents</a>
                    </td>
                </tr>

                <tr v-if="dataset.id">
                    <td>History Content API ID</td>

                    <td>
                        <div id="dataset-id">
                            {{ dataset.id }}
                            <DecodedId :id="dataset.id" />
                        </div>
                    </td>
                </tr>

                <tr v-if="dataset.history_id">
                    <td>History API ID</td>

                    <td>
                        <div id="history_id">
                            {{ dataset.history_id }}
                            <DecodedId :id="dataset.history_id" />
                        </div>
                    </td>
                </tr>

                <tr v-if="dataset.uuid">
                    <td>UUID</td>

                    <td id="dataset-uuid">
                        {{ dataset.uuid }}
                    </td>
                </tr>

                <tr v-if="dataset.file_name">
                    <td>Full Path</td>

                    <td id="file_name">
                        {{ dataset.file_name }}
                    </td>
                </tr>

                <tr v-if="dataset.created_from_basename">
                    <td>Originally Created From a File Named</td>

                    <td id="created_from_basename">
                        {{ dataset.created_from_basename }}
                    </td>
                </tr>

                <tr v-if="dataset.sources && dataset.sources.length > 0">
                    <td>Sources</td>

                    <td>
                        <DatasetSources :sources="dataset.sources" />
                    </td>
                </tr>

                <tr v-if="dataset.hashes && dataset.hashes.length > 0">
                    <td>Hashes</td>

                    <td>
                        <DatasetHashes :hashes="dataset.hashes" />
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>
