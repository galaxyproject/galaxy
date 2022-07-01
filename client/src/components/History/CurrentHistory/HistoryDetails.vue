<template>
    <LayoutDetails
        :name="history.name"
        :annotation="history.annotation"
        :tags="history.tags"
        :writeable="writeable"
        @save="onSave">
        <template v-slot:name>
            <h3 v-short="history.name || 'History'" data-description="name display" class="my-2" />
        </template>
    </LayoutDetails>
</template>

<script>
import short from "components/directives/v-short";
import LayoutDetails from "components/History/Layout/LayoutDetails";

export default {
    components: {
        LayoutDetails,
    },
    directives: {
        short,
    },
    props: {
        history: { type: Object, required: true },
        writeable: { type: Boolean, default: true },
    },
    methods: {
        onSave(newDetails) {
            const id = this.history.id;
            this.$emit("update:history", { ...newDetails, id });
        },
    },
};
</script>
