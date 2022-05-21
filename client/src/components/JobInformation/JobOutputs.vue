<template>
    <div>
        <h3 v-if="title">{{ title }}</h3>
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
    },
    computed: {
        nonHiddenOutputs() {
            return Object.fromEntries(Object.entries(this.jobOutputs).filter(([key, value]) => !key.startsWith("__")));
        },
    },
};
</script>
