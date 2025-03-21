<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import type { TrsTool, TrsToolVersion } from "./types";

library.add(faUpload);

interface Props {
    trsTool: TrsTool;
}

const props = defineProps<Props>();

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
            <b>名称:</b>

            <span>{{ props.trsTool.name }}</span>
        </div>
        <div>
            <b>描述:</b>

            <span>{{ props.trsTool.description }}</span>
        </div>
        <div>
            <b>组织</b>

            <span>{{ props.trsTool.organization }}</span>
        </div>
        <div>
            <b>版本</b>

            <ul>
                <li v-for="version in props.trsTool.versions" :key="version.id">
                    <BButton
                        class="m-1 workflow-import"
                        :data-version-name="version.name"
                        @click="importVersion(version)">
                        {{ version.name }}

                        <FontAwesomeIcon :icon="faUpload" />
                    </BButton>
                </li>
            </ul>
        </div>
    </div>
</template>
