<template>
    <div>
        <div v-for="(elVal, pvIndex) in parameter_value" :key="pvIndex">
            <generic-history-item
                v-if="['hda', 'hdca'].includes(elVal.src)"
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
