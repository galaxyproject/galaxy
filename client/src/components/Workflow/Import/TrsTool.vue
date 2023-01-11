<script setup lang="ts">
import type { TrsTool, TrsToolVersion } from "./types";

const props = defineProps<{ trsTool: TrsTool }>();

const emit = defineEmits<{
    (e: "onImport", versionId: string): void;
}>();

function importVersion(version: TrsToolVersion) {
    const version_id = version.id.includes(`:${version.name}`) ? version.name : version.id;
    emit("onImport", version_id);
}
</script>

<template>
    <div>
        <div>
            <b>Name:</b>
            <span>{{ props.trsTool.name }}</span>
        </div>
        <div>
            <b>Description:</b>
            <span>{{ props.trsTool.description }}</span>
        </div>
        <div>
            <b>Organization</b>
            <span>{{ props.trsTool.organization }}</span>
        </div>
        <div>
            <b>Versions</b>
            <ul>
                <li v-for="version in props.trsTool.versions" :key="version.id">
                    <b-button
                        class="m-1 workflow-import"
                        :data-version-name="version.name"
                        @click="importVersion(version)">
                        {{ version.name }}
                        <icon icon="upload" />
                    </b-button>
                </li>
            </ul>
        </div>
    </div>
</template>
