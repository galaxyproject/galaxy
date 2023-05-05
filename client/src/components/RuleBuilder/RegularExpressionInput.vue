<template>
    <div>
        <label v-b-tooltip.hover for="regular_expression" :title="title">{{ label }}</label>
        <span v-b-popover.html="popoverContent" :title="popoverTitle" class="fa fa-question"></span>
        <input
            v-b-tooltip.hover.left
            :title="title"
            name="regular_expression"
            class="rule-regular-expression"
            type="text"
            :value="target"
            @input="$emit('update:target', $event.target.value)" />
    </div>
</template>

<script>
import { localize } from "utils/localization";

export default {
    props: {
        target: {
            required: true,
        },
    },
    computed: {
        label() {
            return localize("Regular Expression");
        },
        title() {
            return localize("Enter a regular expression.");
        },
        popoverTitle() {
            return localize("Regular Expressions");
        },
        popoverContent() {
            return localize(
                `Regular expressions are patterns used to match character combinations in strings. This input accepts Python-style regular expressions, find more information about these in <a href="https://pythonforbiologists.com/tutorial/regex.html">this Python for Biologists tutorial</a>.`
            );
        },
    },
};
</script>
