<template>
    <div>
        
        <!-- why not this?
        <DatasetProvider :id="hda_id" v-slot="{ dataset }">
        </DatasetProvider> -->

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
                    <td id="created" v-if="dataset.create_time">
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
            </tbody>
        </table>
    </div>
</template>

<script>
import { mapCacheActions } from "vuex-cache";
import Utils from "utils/utils";
import UtcDate from "components/UtcDate";
import DecodedId from "../DecodedId";
import { mapGetters } from "vuex";

export default {
    props: {
        hda_id: {
            type: String,
            required: true,
        },
    },
    components: {
        DecodedId,
        UtcDate,
    },
    created: function () {
        this.fetchDataset(this.hda_id);
    },
    computed: {
        ...mapGetters("datasets", ["getDatasetById"]),
        dataset: function () {
            return this.getDatasetById(this.hda_id);
        },
    },
    methods: {
        bytesToString(raw_size) {
            return Utils.bytesToString(raw_size);
        },
        ...mapCacheActions("datasets", ["fetchDataset"]),
    },
};
</script>
