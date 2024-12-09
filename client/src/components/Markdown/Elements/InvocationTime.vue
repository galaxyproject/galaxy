<template>
    <div class="invocation-time" :invocation_id="args.invocation_id">
        <pre><code>{{ content }}</code></pre>
    </div>
</template>

<script>
import { formatGalaxyPrettyDateString } from "@/utils/dates";

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
            return invocation && formatGalaxyPrettyDateString(invocation["create_time"]);
        },
    },
};
</script>
