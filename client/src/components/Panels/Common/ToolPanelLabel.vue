<template>
    <div class="tool-panel-label">
        {{ definition.text }}
    </div>
</template>

<script>
export default {
    props: {
        definition: {
            type: Object,
            required: true,
        },
    },
};
</script>
