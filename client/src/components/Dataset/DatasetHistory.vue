<template>
    <div>
        {{ historyName }}
    </div>
</template>
<script>
import { mapState } from "pinia";
import { useHistoryStore } from "stores/historyStore";

export default {
    props: {
        item: Object,
    },
    computed: {
        ...mapState(useHistoryStore, ["getHistoryNameById"]),
        historyName() {
            return this.getHistoryNameById(this.item.history_id);
        },
    },
};
</script>
