<template>
    <GCard :title="title" class="mx-4 icon-card">
        <GContainer class="p-0">
            <GRow>
                <GCol>
                    {{ description }}
                </GCol>
                <GCol cols="auto">
                    <i :class="icon" />
                </GCol>
            </GRow>
        </GContainer>
        <GButton variant="primary" @click="onButtonClick">
            {{ buttonText }}
        </GButton>
    </GCard>
</template>

<script>
import { GButton, GCard, GCol, GContainer, GRow } from "@/component-library";

/** A generic Card, used as a template, that displays an action button,
 * an icon (font-awesome), along with a title and description.
 * Clicking the button emits an "onButtonClick" event. */

export default {
    components: {
        GButton,
        GContainer,
        GCard,
        GRow,
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
