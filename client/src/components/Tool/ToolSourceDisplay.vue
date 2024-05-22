<template>
    <Prism :language="language" :code="code" :plugins="['normalize-whitespace']"></Prism>
</template>

<script>
import "prismjs/themes/prism.css";
import "prismjs/plugins/normalize-whitespace/prism-normalize-whitespace.js";

import Prism from "vue-prismjs";

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
