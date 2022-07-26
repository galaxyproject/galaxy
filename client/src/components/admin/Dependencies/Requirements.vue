<template>
    <span class="requirements-cell">
        <span v-if="requirements.length == 0">
            <i>no requirements defined</i>
        </span>
        <div v-for="(requirement, index) in requirements" v-else :key="index">
            <requirement :requirement="requirement" />
        </div>
    </span>
</template>
<script>
import Requirement from "./Requirement";

export default {
    components: { Requirement },
    props: {
        requirements: {
            type: Array,
            required: true,
        },
    },
};
</script>
