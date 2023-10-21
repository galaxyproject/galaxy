<template>
    <div class="invocation-time" :invocation_id="args.invocation_id">
        <pre><code>{{ content }}</code></pre>
    </div>
</template>

<script>
export default {
    props: {
        args: {
            type: Object,
            required: true,
        },
        invocations: {
            type: Object,
            required: true,
        },
    },
    computed: {
        content() {
            const invocation = this.invocations[this.args.invocation_id];
            return invocation && new Date(invocation["create_time"]).toUTCString();
        },
    },
};
</script>
