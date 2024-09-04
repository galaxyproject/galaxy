<template>
    <div>
        <div v-for="(elVal, pvIndex) in parameter_value" :key="pvIndex">
            <span v-if="elVal === null">No input provided</span>
            <GenericHistoryItem
                v-else-if="['hda', 'hdca', 'dce'].includes(elVal.src)"
                :item-id="elVal.id"
                :item-src="elVal.src" />
            <span v-else> {{ elVal.hid }}: {{ elVal.name }} </span>
        </div>
    </div>
</template>

<script>
import GenericHistoryItem from "components/History/Content/GenericItem";

export default {
    components: {
        GenericHistoryItem,
    },
    props: {
        parameter_value: {
            type: Array,
        },
    },
};
</script>
