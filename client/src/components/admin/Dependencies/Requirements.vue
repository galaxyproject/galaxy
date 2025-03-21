<template>
    <span class="requirements-cell">
        <span v-if="requirements.length == 0">
            <i>无定义的需求</i>
        </span>
        <div v-for="(requirement, index) in requirements" v-else :key="index">
            <Requirement :requirement="requirement" />
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
