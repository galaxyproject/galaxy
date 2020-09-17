<template>
    <div>
        {{ historyName }}
    </div>
</template>
<script>
import { mapGetters } from "vuex";

export default {
    props: {
        item: Object,
    },
    computed: {
        ...mapGetters(["getHistoryNameById"]),
        historyName() {
            return this.getHistoryNameById(this.item.history_id);
        },
    },
};
</script>
