<template>
    <DatasetProvider :id="hda_id" v-slot="{ result: dataset, loading }">
        <div v-if="!loading">
            <h3>Dataset Information</h3>
            <table id="dataset-details" class="tabletip info_data_table">
                <tbody>
                    <tr>
                        <td>Number</td>
                        <td id="number">{{ dataset.hid }}</td>
                    </tr>
                    <tr>
                        <td>Name</td>
                        <td id="name">{{ dataset.name }}</td>
                    </tr>
                    <tr>
                        <td>Created</td>
                        <td v-if="dataset.create_time" id="created">
                            <UtcDate :date="dataset.create_time" mode="pretty" />
                        </td>
                    </tr>
                    <tr>
                        <td>Filesize</td>
                        <td id="filesize" v-html="bytesToString(dataset.file_size)"></td>
                    </tr>
                    <tr>
                        <td>Dbkey</td>
                        <td id="dbkey">{{ dataset.metadata_dbkey }}</td>
                    </tr>
                    <tr>
                        <td>Format</td>
                        <td id="format">{{ dataset.file_ext }}</td>
                    </tr>
                    <tr>
                        <td>File contents</td>
                        <td id="file-contents"><a :href="dataset.download_url">contents</a></td>
                    </tr>
                    <tr v-if="dataset.id">
                        <td>History Content API ID</td>
                        <td>
                            <div id="dataset-id">{{ dataset.id }} <decoded-id :id="dataset.id" /></div>
                        </td>
                    </tr>
                    <tr v-if="dataset.history_id">
                        <td>History API ID</td>
                        <td>
                            <div id="history_id">{{ dataset.history_id }} <decoded-id :id="dataset.history_id" /></div>
                        </td>
                    </tr>
                    <tr v-if="dataset.uuid">
                        <td>UUID</td>
                        <td id="dataset-uuid">{{ dataset.uuid }}</td>
                    </tr>
                    <tr v-if="dataset.file_name">
                        <td>Full Path</td>
                        <td id="file_name">{{ dataset.file_name }}</td>
                    </tr>
                    <tr v-if="dataset.created_from_basename">
                        <td>Originally Created From a File Named</td>
                        <td id="created_from_basename">{{ dataset.created_from_basename }}</td>
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
    </DatasetProvider>
</template>

<script>
import Utils from "utils/utils";
import UtcDate from "components/UtcDate";
import DecodedId from "../DecodedId";
import { DatasetProvider } from "components/providers";
import DatasetSources from "./DatasetSources";
import DatasetHashes from "./DatasetHashes";

export default {
    components: {
        DatasetHashes,
        DatasetProvider,
        DatasetSources,
        DecodedId,
        UtcDate,
    },
    props: {
        hda_id: {
            type: String,
            required: true,
        },
    },
    methods: {
        bytesToString(raw_size) {
            return Utils.bytesToString(raw_size);
        },
    },
};
</script>
