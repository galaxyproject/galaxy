<template>
    <prism :language="language" :code="code" :plugins="['normalize-whitespace']"></prism>
</template>

<script>
import Prism from "vue-prismjs";
import "prismjs/themes/prism.css";
import "prismjs/plugins/normalize-whitespace/prism-normalize-whitespace.js";

export default {
    components: {
        Prism,
    },
    props: {
        language: {
            type: String,
            required: true,
        },
        code: {
            type: String,
            required: true,
        },
    },
};
</script>
