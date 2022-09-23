<script setup>
import Heading from "./Common/Heading.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDoubleRight, faAngleRight, faQuestion } from "@fortawesome/free-solid-svg-icons";
import { faQuestionCircle } from "@fortawesome/free-regular-svg-icons";

library.add(faAngleDoubleRight);
library.add(faAngleRight);
library.add(faQuestion);
library.add(faQuestionCircle);
</script>

<template>
    <div>
        <Heading>Default Heading</Heading>
        <Heading h2 size="xl">Large H2 Heading</Heading>
        <Heading h3 separator size="md">Medium H3 Heading with Separator</Heading>
        <Heading h3 size="md" icon="fa-angle-right">Heading with Icon</Heading>
        <Heading h4 size="sm" icon="fa-angle-double-right">Small Heading with Icon</Heading>
        <Heading h2 bold size="md">Medium Bold H2</Heading>
        <span> <Heading h3 bold inline size="text">Inline Text Sized Bold H3</Heading> next to some text.</span>
        <Heading h3 separator bold size="md">Bold H3 with Separator</Heading>
        <Heading h4 bold size="md" icon="fa-question">Bold Medium H4 with Icon</Heading>
        <Heading h4 size="sm" icon="far fa-question-circle">Small H4 with Icon</Heading>
        <Heading h3 separator size="sm">Small H3 with Separator</Heading>
    </div>
</template>
