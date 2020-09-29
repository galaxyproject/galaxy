<template>
    <div>
        <h3>Dataset Information</h3>
        <table id="dataset_information" class="tabletip info_data_table">
            <tbody>
                <tr>
                    <td>Number</td>
                    <td>{{ dataset.hid }}</td>
                </tr>
                <tr>
                    <td>Name</td>
                    <td>{{ dataset.name }}</td>
                </tr>
                <tr>
                    <td>Created</td>
                    <td v-if="dataset.create_time">
                        <UtcDate :date="dataset.create_time" mode="pretty" />
                    </td>
                </tr>
                <tr>
                    <td>Filesize</td>
                    <td v-html="bytesToString(dataset.file_size)"></td>
                </tr>
                <tr>
                    <td>Dbkey</td>
                    <td>{{ dataset.metadata_dbkey }}</td>
                </tr>
                <tr>
                    <td>Format</td>
                    <td>{{ dataset.file_ext }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script>
import { mapCacheActions } from "vuex-cache";
import Utils from "utils/utils";
import UtcDate from "components/UtcDate";

export default {
    props: {
        hda_id: {
            type: String,
            required: true,
        },
    },
    components: {
        UtcDate,
    },
    created: function () {
        this.fetchDataset(this.hda_id);
    },
    computed: {
        dataset: function () {
            console.log(this.$store.getters.dataset(this.hda_id));
            console.log(this.$store.getters.dataset(this.hda_id));
            console.log(this.$store.getters.dataset(this.hda_id));
            console.log(this.$store.getters.dataset(this.hda_id));
            console.log(this.$store.getters.dataset(this.hda_id));
            console.log(this.$store.getters.dataset(this.hda_id));
            console.log(this.$store.getters.dataset(this.hda_id));
            console.log(this.$store.getters.dataset(this.hda_id));
            return this.$store.getters.dataset(this.hda_id);
        },
    },
    methods: {
        bytesToString(raw_size) {
            return Utils.bytesToString(raw_size);
        },
        ...mapCacheActions(["fetchDataset"]),
    },
};
</script>
