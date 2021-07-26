<template>
    <div>
        <h3 v-if="title">{{ title }}</h3>
        <table class="tabletip info_data_table" id="job-outputs">
            <thead>
                <tr>
                    <th>Tool Outputs</th>
                    <th>Dataset</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(value, name) in nonHiddenOutputs" :key="name">
                    <td>
                        {{ value[0].label || name }}
                    </td>
                    <td>
                        <workflow-invocation-data-contents
                            v-for="(item, index) in value"
                            :key="index"
                            :data_item="item.value"
                        />
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script>
import WorkflowInvocationDataContents from "components/WorkflowInvocationState/WorkflowInvocationDataContents";

export default {
    components: {
        WorkflowInvocationDataContents,
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
