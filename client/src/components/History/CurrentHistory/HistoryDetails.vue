<template>
    <Details
        :name="history.name"
        :annotation="history.annotation"
        :tags="history.tags"
        :writeable="writeable"
        @save="onSave">
        <template v-slot:name>
            <h3 data-description="name display" v-short="history.name || 'History'" />
            <h5 class="history-size mt-1">
                <span v-if="history.size">
                    <div>{{ history.size | niceFileSize }}</div>
                    <div>{{ shownCount }} shown, {{ hiddenCount }} hidden</div>
                </span>
                <span v-else v-localize>(empty)</span>
            </h5>
        </template>
    </Details>
</template>

<script>
import prettyBytes from "pretty-bytes";
import store from "store";
import short from "components/directives/v-short";
import Details from "components/History/Layout/Details";

export default {
    components: {
        Details,
    },
    directives: {
        short,
    },
    filters: {
        niceFileSize(rawSize = 0) {
            return prettyBytes(rawSize);
        },
    },
    props: {
        history: { type: Object, required: true },
        writeable: { type: Boolean, default: true },
    },
    computed: {
        shownCount() {
            return store.getters.getHistoryItems({ historyId: this.history.id, filterText: "" }).length;
        },
        hiddenCount() {
            return store.getters.getHistoryItems({ historyId: this.history.id, filterText: "visible=false" }).length;
        },
    },
    methods: {
        onSave(newDetails) {
            const id = this.history.id;
            this.$emit("updateHistory", { ...newDetails, id });
        },
    },
};
</script>
