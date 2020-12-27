<template>
    <b-list-group>
        <b-list-group-item
            class="rounded-0"
            v-for="opt in suggestions"
            :key="opt.value"
            button
            size="sm"
            :active="opt.active"
            @click="$emit('onSelect', opt)"
            v-html="opt.label"
        ></b-list-group-item>
    </b-list-group>
</template>

<script>
import { BListGroup, BListGroupItem } from "bootstrap-vue";

export default {
    components: {
        BListGroup,
        BListGroupItem,
    },
    props: {
        suggestions: { type: Array, default: () => [] },
    },
};
</script>
