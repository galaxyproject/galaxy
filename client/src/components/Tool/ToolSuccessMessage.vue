<template>
    <div class="donemessagelarge">
        <p>
            已启动工具 <b>{{ toolName }}</b> 并成功将{{ nJobsText }}添加到队列中。
        </p>
        <p>它产生了{{ nOutputsText }}：</p>
        <ul>
            <li v-for="item of jobResponse.outputs" :key="item.hid">
                <b>{{ item.hid }}: {{ item.name }}</b>
            </li>
        </ul>
        <p>
            您可以通过刷新历史面板来查看队列中作业的状态和查看结果数据。当作业运行完成后，
            如果成功完成，状态将从"运行中"变为"已完成"；如果遇到问题，则变为"错误"。
        </p>
    </div>
</template>

<script>
export default {
    props: {
        jobResponse: {
            type: Object,
            required: true,
        },
        toolName: {
            type: String,
            required: true,
        },
    },
    computed: {
        nOutputs() {
            return this.jobResponse && this.jobResponse.outputs ? this.jobResponse.outputs.length : 0;
        },
        nJobs() {
            return this.jobResponse && this.jobResponse.jobs ? this.jobResponse.jobs.length : 0;
        },
        nJobsText() {
            return this.nJobs > 1 ? `${this.nJobs} 个作业` : `1 个作业`;
        },
        nOutputsText() {
            return this.nOutputs > 1 ? `${this.nOutputs} 个输出` : `此输出`;
        },
    },
};
</script>
