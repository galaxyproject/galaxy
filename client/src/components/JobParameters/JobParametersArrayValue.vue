<template>
    <div>
        <div v-for="(elVal, pvIndex) in parameter_value" :key="pvIndex">
            <generic-history-content v-if="['hda', 'hdca'].includes(elVal.src)" :data_item="elVal" />
            <span v-else> {{ elVal.hid }}: {{ elVal.name }} </span>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import GenericHistoryContent from "components/History/Content/GenericContentItem/GenericHistoryContent";

Vue.use(BootstrapVue);

export default {
    components: {
        GenericHistoryContent,
    },
    props: {
        parameter_value: {
            type: Array,
        },
    },
};
</script>
