<template>
    <div>
        <label v-b-tooltip.hover for="regular_expression" :title="title">{{ label }}</label>
        <FontAwesomeIcon v-b-popover.html="popoverContent" :title="popoverTitle" icon="fa-question" />
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
import _l from "utils/localization";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion } from "@fortawesome/free-solid-svg-icons";

library.add(faQuestion);

export default {
    components: { FontAwesomeIcon },
    props: {
        target: {
            required: true,
        },
    },
    computed: {
        label() {
            return _l("Regular Expression");
        },
        title() {
            return _l("Enter a regular expression.");
        },
        popoverTitle() {
            return _l("Regular Expressions");
        },
        popoverContent() {
            return _l(
                `Regular expressions are patterns used to match character combinations in strings. This input accepts Python-style regular expressions, find more information about these in <a href="https://pythonforbiologists.com/tutorial/regex.html">this Python for Biologists tutorial</a>.`
            );
        },
    },
};
</script>
