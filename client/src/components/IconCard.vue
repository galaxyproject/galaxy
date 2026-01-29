<template>
    <b-card :title="title" class="mx-4 icon-card">
        <b-container class="p-0">
            <b-row>
                <b-col>{{ description }}</b-col>
                <b-col cols="auto"><i :class="icon"></i></b-col>
            </b-row>
        </b-container>
        <GButton color="blue" @click="onButtonClick">{{ buttonText }}</GButton>
    </b-card>
</template>

<script>
import GButton from "./BaseComponents/GButton.vue";

/** A generic Card, used as a template, that displays an action button,
 * an icon (font-awesome), along with a title and description.
 * Clicking the button emits an "onButtonClick" event. */
export default {
    components: { GButton },
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
