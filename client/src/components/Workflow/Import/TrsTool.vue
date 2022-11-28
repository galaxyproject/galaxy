<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = defineProps({
    trsTool: {
        type: Object,
        required: true,
    },
});

const emit = defineEmits(["onImport"]);

const importVersion = (version) => {
    const version_id = version.id.includes(`:${version.name}`) ? version.name : version.id;
    emit("onImport", version_id);
};
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUpload } from "@fortawesome/free-solid-svg-icons";

library.add(faUpload);
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
                        <FontAwesomeIcon icon="upload" />
                    </b-button>
                </li>
            </ul>
        </div>
    </div>
</template>
