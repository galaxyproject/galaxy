<template>
    <GCard nobody class="content-height">
        <div :class="name" :job_id="args.job_id">
            <pre><code class="word-wrap-normal">{{ jobContent }}</code></pre>
        </div>
    </GCard>
</template>

<script>
import GCard from "@/component-library/GCard.vue";

export default {
    components: {
        GCard,
    },
    props: {
        args: {
            type: Object,
            required: true,
        },
        name: {
            type: String,
            required: true,
        },
        jobs: {
            type: Object,
            default: null,
        },
    },
    computed: {
        jobContent() {
            const job = this.jobs[this.args.job_id];
            return job && job[this.name];
        },
    },
};
</script>
<style scoped>
.content-height {
    max-height: 15rem;
    overflow-y: auto;
}
</style>
