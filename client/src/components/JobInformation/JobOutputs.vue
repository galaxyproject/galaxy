<template>
    <div>
        <h2 v-if="title" class="h-md">
            {{ title }}
            <span v-if="paginate && totalLength > firstN"> (showing {{ firstN }} of {{ totalLength }}) </span>
        </h2>
        <table id="job-outputs" class="tabletip info_data_table">
            <thead>
                <tr>
                    <th>Tool Outputs</th>
                    <th>Dataset</th>
                </tr>
            </thead>
            <tbody v-if="jobOutputs">
                <tr v-for="(value, name) in nonHiddenOutputs" :key="name">
                    <td>
                        {{ value[0].label || name }}
                    </td>
                    <td>
                        <generic-history-item
                            v-for="(item, index) in value"
                            :key="index"
                            :item-id="item.value.id"
                            :item-src="item.value.src" />
                    </td>
                </tr>
                <tr v-if="paginate && totalLength > firstN">
                    <td colspan="2">
                        <b-button id="paginate-btn" block variant="secondary" @click="firstN += 10">
                            Show {{ totalLength - firstN >= 10 ? 10 : totalLength - firstN }} more outputs
                        </b-button>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script>
import GenericHistoryItem from "components/History/Content/GenericItem";

export default {
    components: {
        GenericHistoryItem,
    },
    props: {
        jobOutputs: Object,
        title: {
            type: String,
            required: false,
        },
        paginate: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            firstN: 10,
        };
    },
    computed: {
        entries() {
            return Object.entries(this.jobOutputs).filter(([key, value]) => !key.startsWith("__"));
        },
        nonHiddenOutputs() {
            if (this.paginate) {
                return Object.fromEntries(this.entries.slice(0, this.firstN));
            } else {
                return Object.fromEntries(this.entries);
            }
        },
        totalLength() {
            return this.entries.length;
        },
    },
};
</script>
