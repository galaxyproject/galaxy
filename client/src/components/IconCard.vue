<template>
    <b-card :title="title" class="mx-4 icon-card">
        <b-container class="p-0">
            <b-row>
                <GCol>{{ description }}</GCol>
                <GCol cols="auto"><i :class="icon"></i></GCol>
            </b-row>
        </b-container>
        <GButton variant="primary" @click="onButtonClick">{{ buttonText }}</GButton>
    </b-card>
</template>

<script>
/** A generic Card, used as a template, that displays an action button,
 * an icon (font-awesome), along with a title and description.
 * Clicking the button emits an "onButtonClick" event. */
import GButton from "component-library/GButton";

import GCol from "@/component-library/GCol.vue";

export default {
    components: {
        GButton,
        GCol,
    },
    props: {
        title: {
            type: String,
            required: true,
        },
        description: {
            type: String,
            required: true,
        },
        icon: {
            type: String,
            required: true,
        },
        buttonText: {
            type: String,
            required: true,
        },
    },
    methods: {
        onButtonClick() {
            this.$emit("onButtonClick");
        },
    },
};
</script>

<style scoped>
.icon-card {
    max-width: 500px;
}
</style>
