<script setup lang="ts">
import { computed } from "vue";

import DirectiveHelpSection from "./DirectiveHelpSection.vue";

interface MarkdownHelpProps {
    mode: "report" | "page";
}

const props = defineProps<MarkdownHelpProps>();

const page = computed(() => props.mode == "page");
</script>

<template>
    <div>
        <h3>概览</h3>
        <p>
            <span v-if="page"> 这个Markdown文档将用于生成您的Galaxy页面。 </span>
            <span v-else> 这个Markdown文档将用于生成您的工作流调用报告。 </span>
            本文档应为Markdown格式，并嵌入用于提取和显示Galaxy对象及其元数据的命令。
        </p>

        <p>
            有关标准Markdown的概述，请访问
            <a href="https://commonmark.org/help/tutorial/">commonmark.org教程</a>。
        </p>

        <p>
            Galaxy对Markdown的扩展表示为代码块，这些块以<tt>```galaxy</tt>行开始，以<tt>```</tt>行结束，并在这些行之间包含带参数的命令。
            <span v-if="page">
            这些参数引用您的Galaxy对象，如数据集、作业和工作流。
            </span>
            <span v-else>
            这些参数通过标签引用工作流的各个部分，如步骤、输入和输出。
            </span>
        </p>

        <h3>历史内容命令</h3>

        <p>
            这些命令引用数据集或数据集集合。例如，以下示例将显示数据集集合的元数据，并将数据集作为图像嵌入到文档中。

            <span v-if="page">
            这些元素通过Galaxy API使用的对象ID进行引用。Markdown编辑器将允许您以图形方式选择对象，但它们将通过这些ID嵌入到Markdown中。
            </span>

            <span v-else>
            这些元素通过工作流的输入或输出标签进行引用。如果您想要引用的数据集或集合在Markdown编辑器中不可供选择，请确保首先在工作流编辑器中为该对象分配标签。
            </span>
        </p>

        <pre v-if="page">
```galaxy
history_dataset_collection_display(history_dataset_collection_id=33b43b4e7093c91f)
```
</pre
        >
        <pre v-else>
```galaxy
history_dataset_collection_display(output=mapped_bams)
```
</pre
        >

        <pre v-if="page">
```galaxy
history_dataset_as_image(history_dataset_id=33b43b4e7093c91f)
```
</pre
        >
        <pre v-else>
```galaxy
history_dataset_as_image(output=normalized_result_plot)
```
</pre
        >

        <DirectiveHelpSection
            :mode="mode"
            :directives="[
                'history_dataset_display',
                'history_dataset_collection_display',
                'history_dataset_as_image',
                'history_dataset_as_table',
                'history_dataset_peek',
                'history_dataset_info',
            ]" />

        <h3>工作流命令</h3>

        <p v-if="page">
            这些命令通过对象ID引用工作流。以下示例将在生成的Galaxy页面中显示工作流的表示：
        </p>
        <p v-else>这些命令引用当前工作流，大多数情况下不需要输入参数。</p>


        <pre v-if="page">
```galaxy
workflow_display(workflow_id=33b43b4e7093c91f>)
```
</pre
        >
        <pre v-else>
```galaxy
workflow_display()
```
            </pre
        >

        <DirectiveHelpSection
            :mode="mode"
            :directives="['workflow_license', 'workflow_display', 'workflow_image', 'invocation_time']" />

        <h3>作业命令</h3>

        <p v-if="page">
            这些命令引用Galaxy作业。例如，以下示例将显示作业ID为<tt>33b43b4e7093c91f</tt>的作业参数。
        </p>
        <p v-else>
            这些命令引用与工作流中标记步骤相关联的Galaxy作业或作业集合。例如，以下示例将显示标签为<tt>mapping</tt>的步骤的作业参数。
        </p>

        <pre v-if="page">
```galaxy
job_parameters(job_id=33b43b4e7093c91f)
```
</pre
        >
        <pre v-else>
```galaxy
job_parameters(step=mapping)
```
            </pre
        >

        <DirectiveHelpSection
            :mode="mode"
            :directives="['tool_stderr', 'tool_stdout', 'job_metrics', 'job_parameters']" />
    </div>
</template>
