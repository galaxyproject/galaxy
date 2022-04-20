<template>
    <div class="ml-1 mt-1">
        <b-button size="sm" class="text-decoration-none" variant="link" @click="close">
            <icon icon="angle-double-left" class="mr-1" data-description="back to history" /><span>History</span>
        </b-button>
        <b-button v-if="previousName" size="sm" class="text-decoration-none" variant="link" @click="back">
            <span class="fa fa-angle-left mr-1" /><span>{{ previousName }}</span>
        </b-button>
    </div>
</template>

<script>
export default {
    props: {
        selectedCollections: { type: Array, required: true, validate: (val) => val.length > 0 },
    },
    computed: {
        previousName() {
            const length = this.selectedCollections.length;
            if (length > 1) {
                const last = this.selectedCollections[length - 2];
                return last.name || last.element_identifier;
            }
            return null;
        },
    },
    methods: {
        back() {
            const newList = this.selectedCollections.slice(0, -1);
            this.$emit("update:selected-collections", newList);
        },
        close() {
            this.$emit("update:selected-collections", []);
        },
    },
};
</script>
