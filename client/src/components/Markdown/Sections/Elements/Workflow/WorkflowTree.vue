<template>
    <div>
        <span v-if="!skipHead">
            <span v-if="input.title" class="font-weight-light">{{ input.title }}:</span>
            <span v-if="input.label" class="font-weight-light">{{ input.label }}</span>
            <span v-if="input.value" class="font-weight-light font-italic">= {{ input.value }}</span>
        </span>
        <div v-if="input && input.inputs && input.inputs.length" :class="{ 'ml-3': !skipHead }">
            <WorkflowInput v-for="child in input.inputs" :key="child.id" :input="child" />
        </div>
    </div>
</template>

<script>
export default {
    name: "WorkflowInput",
    props: {
        input: {
            type: Object,
            default: null,
        },
        skipHead: {
            type: Boolean,
            default: false,
        },
    },
};
</script>
