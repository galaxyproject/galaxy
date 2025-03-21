<template>
    <div class="p-4">
        <h2 class="h-md">工作流报告</h2>
        <p>
            您看到的<b>Markdown</b>文档将用于生成工作流调用报告。您可以使用Markdown嵌入命令，用于提取和显示工作流的各个部分、其调用元数据、输入和输出等。
        </p>
        <div v-html="markdownGeneralHelpHtml" />
        <h2 class="h-md">工作流命令</h2>
        <p>
            这些命令不需要任何参数，并且引用整个工作流。例如，以下示例将在生成的报告中显示工作流的表示：
        </p>
        <pre>
```galaxy
workflow_display()
```
</pre
        >
        <dl>
            <dt><tt>workflow_display</tt></dt>
            <dd>在生成的报告中嵌入工作流本身的描述。</dd>
            <dt><tt>invocation_inputs</tt></dt>
            <dd>在生成的报告中嵌入标记的工作流输入。</dd>
            <dt><tt>invocation_outputs</tt></dt>
            <dd>在生成的报告中嵌入标记的工作流输出。</dd>
        </dl>
        <h2 class="h-md">步骤命令</h2>
        <p>
            这些命令引用工作流步骤标签，并指向与该步骤对应的作业。当前的一个限制是，如果这些命令引用集合映射步骤，报告将会中断，这些命令必须标识单个作业。例如，以下示例将显示标记为'qc'的步骤运行时使用的作业参数：
        </p>
        <pre>
```galaxy
job_parameters(step="qc")
```
</pre
        >
        <p>也可以引用单个作业参数</p>

        <pre>
```galaxy
job_parameters(step="qc", param="parameter_text")
```
</pre
        >
        <dt><tt>tool_stderr</tt></dt>
        <dd>在生成的报告中嵌入此步骤的工具标准错误流。</dd>
        <dt><tt>tool_stdout</tt></dt>
        <dd>在生成的报告中嵌入此步骤的工具标准输出流。</dd>
        <dt><tt>job_metrics</tt></dt>
        <dd>在生成的报告中嵌入此步骤的作业指标（如果用户有权限）。</dd>
        <dt><tt>job_parameters</tt></dt>
        <dd>在生成的报告中嵌入此步骤的工具参数。</dd>
        <h2 class="h-md">输入/输出命令</h2>
        <p>
            这些命令通过标签引用工作流输入或输出。例如，以下示例将显示对应于输出"Merged BAM"的数据集集合：
        </p>

        <pre>
```galaxy
history_dataset_collection_display(output="Merged Bam")
```
</pre
        >
        <div v-html="datasetCommandsHtml" />
    </div>
</template>

<script>
import { datasetCommandsHtml, markdownGeneralHelpHtml } from "components/Markdown/help";

export default {
    data() {
        return {
            datasetCommandsHtml,
            markdownGeneralHelpHtml,
        };
    },
};
</script>
