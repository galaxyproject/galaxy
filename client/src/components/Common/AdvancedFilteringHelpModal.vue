<script setup lang="ts">
import { BModal } from "bootstrap-vue";

type FilterOption = {
    filter: string;
    description: string;
};

interface Props {
    visible: boolean;
    title: string;
    filterOptions?: FilterOption[];
}

withDefaults(defineProps<Props>(), {
    title: "",
    filterOptions: () => [
        { filter: "name", description: "Shows items with the given sequence of characters in their names." },
    ],
});

defineEmits<{
    (e: "close"): void;
}>();
</script>

<template>
    <BModal :visible="visible" :title="`Filtering Options Help - ${title}`" ok-only @ok="() => $emit('close')">
        <div>
            <p>This input can be used to filter the {{ title }} displayed.</p>

            <p>
                Text entered here will be searched against {{ title }}. Additionally, advanced filtering tags can be
                used to refine the search more precisely. Filtering tags are of the form
                <code>&lt;tag_name&gt;:&lt;tag_value&gt;</code> or <code>&lt;tag_name&gt;:'&lt;tag_value&gt;'</code>.
                For instance to search just for RNAseq in the {{ title }} name, <code>name:rnsseq</code> can be used.
                Notice by default the search is not case-sensitive. If the quoted version of tag is used, the search is
                case sensitive and only full matches will be returned. So <code>name:'RNAseq'</code> would show only
                {{ title }} named exactly <code>RNAseq</code>.
            </p>

            <p>The available filtering tags are:</p>
            <dl>
                <div v-for="(fo, index) in filterOptions" :key="index" class="mb-2">
                    <dt>
                        <code>{{ fo.filter }}</code>
                    </dt>
                    <dd>{{ fo.description }}</dd>
                </div>
            </dl>
        </div>
    </BModal>
</template>
