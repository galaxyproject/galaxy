<template>
    <DetailsLayout
        :name="history.name"
        :annotation="history.annotation"
        :tags="history.tags"
        :writeable="writeable"
        @save="onSave">
        <template v-slot:name>
            <!-- eslint-disable-next-line vuejs-accessibility/heading-has-content -->
            <h3 v-short="history.name || 'History'" data-description="name display" class="my-2" />
        </template>
    </DetailsLayout>
</template>

<script>
import { mapActions } from "pinia";
import { useHistoryStore } from "@/stores/historyStore";
import short from "@/components/plugins/short.js";
import DetailsLayout from "@/components/History/Layout/DetailsLayout.vue";

export default {
    components: {
        DetailsLayout,
    },
    directives: {
        short,
    },
    props: {
        history: { type: Object, required: true },
        writeable: { type: Boolean, default: true },
    },
    methods: {
        ...mapActions(useHistoryStore, ["updateHistory"]),
        onSave(newDetails) {
            const id = this.history.id;
            this.updateHistory({ ...newDetails, id });
        },
    },
};
</script>
