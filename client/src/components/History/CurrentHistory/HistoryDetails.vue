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
import short from "components/directives/v-short";
import DetailsLayout from "components/History/Layout/DetailsLayout";

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
        onSave(newDetails) {
            const id = this.history.id;
            this.$emit("update:history", { ...newDetails, id });
        },
    },
};
</script>
