<template>
    <b-dropdown text="Select history..." size="sm">
        <b-dropdown-item
            v-for="h in availableHistories"
            :key="h.id"
            :active="value == h.id"
            @click="$emit('input', h.id)"
        >
            {{ h.name }}
        </b-dropdown-item>
    </b-dropdown>
</template>

<script>
import { mapGetters } from "vuex";

export default {
    props: {
        value: { type: String, required: true },
    },
    computed: {
        ...mapGetters("betaHistory", ["activeHistories"]),

        availableHistories() {
            return Array.from(this.activeHistories).sort((a, b) => {
                const aa = a.name.toLowerCase();
                const bb = b.name.toLowerCase();
                return bb - aa;
            });
        },
    },
};
</script>
