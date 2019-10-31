<template>
    <span class="requirement">
        <b class="requirement-name">{{ requirement.name }}</b>
        <span v-if="requirement.version" class="requirement-version">@{{ requirement.version }}</span>
    </span>
</template>
<script>
export default {
    props: {
        requirement: {
            type: Object,
            required: true
        }
    }
};
</script>
