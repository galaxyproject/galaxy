<template>
    <div class="w-50 p-2 float-left">
        <b-card nobody class="content-height">
            <div :class="name" :job_id="args.job_id">
                <pre><code class="text-normalwrap">{{ jobContent }}</code></pre>
            </div>
        </b-card>
    </div>
</template>

<script>
export default {
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
}
</style>
