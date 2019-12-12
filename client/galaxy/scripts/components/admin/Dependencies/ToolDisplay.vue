<template>
    <span class="tool-display">
        <b class="tool-id">{{ toolId }}</b
        ><span v-if="showVersion">@{{ toolVersion }}</span>
    </span>
</template>
<script>
export default {
    props: {
        toolId: {
            type: String,
            required: true
        },
        toolVersion: {
            type: String,
            default: null
        }
    },
    computed: {
        showVersion: function() {
            return this.toolVersion && !this.toolId.endsWith(this.toolVersion);
        }
    }
};
</script>
