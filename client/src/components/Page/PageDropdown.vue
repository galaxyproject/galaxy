<script setup lang="ts">
import _l from "@/utils/localization";
import { computed, unref } from "vue";
import { deletePage } from "./services";
import { storeToRefs } from "pinia";
import { useUserStore } from "@/stores/userStore";

interface Page {
    id: string;
    shared?: Boolean;
    title?: string;
    description?: string;
}
interface PageDropdownProps {
    page: Page;
    root: string;
    published?: Boolean;
}

const props = defineProps<PageDropdownProps>();
const { isAnonymous } = storeToRefs(useUserStore());

const emit = defineEmits(["onRemove", "onSuccess", "onError"]);

const urlEdit = computed(() => `${props.root}pages/editor?id=${props.page.id}`);
const urlEditAttributes = computed(() => `${props.root}pages/edit?id=${props.page.id}`);
const urlShare = computed(() => `${props.root}pages/sharing?id=${props.page.id}`);
const urlView = computed(() => `${props.root}published/page?id=${props.page.id}`);
const readOnly = computed(() => props.page.shared || props.published || unref(isAnonymous));

function onDelete() {
    const confirmationMessage = _l(`Are you sure you want to delete page`) + ` "${props.page.title}"?`;
    if (window.confirm(confirmationMessage)) {
        deletePage(props.page.id)
            .then((response) => {
                emit("onRemove", props.page.id);
                emit("onSuccess");
            })
            .catch((error) => {
                emit("onError", error);
            });
    }
}
</script>
<template>
    <div>
        <b-link
            class="page-dropdown"
            data-toggle="dropdown"
            aria-haspopup="true"
            :data-page-dropdown="props.page.id"
            aria-expanded="false">
            <Icon icon="caret-down" class="fa-lg" />
            <span class="page-title">{{ props.page.title }}</span>
        </b-link>
        <p v-if="props.page.description">{{ props.page.description }}</p>
        <div class="dropdown-menu" aria-labelledby="page-dropdown">
            <a class="dropdown-item dropdown-item-view" :href="urlView">
                <span class="fa fa-eye fa-fw mr-1" />
                <span>View</span>
            </a>
            <a v-if="!readOnly" class="dropdown-item dropdown-item-edit" :href="urlEdit">
                <span class="fa fa-edit fa-fw mr-1" />
                <span>Edit content</span>
            </a>
            <a v-if="!readOnly" class="dropdown-item dropdown-item-edit-attributes" :href="urlEditAttributes">
                <span class="fa fa-pencil fa-fw mr-1" />
                <span>Edit attributes</span>
            </a>
            <a v-if="!readOnly" class="dropdown-item dropdown-item-share" :href="urlShare">
                <span class="fa fa-share-alt fa-fw mr-1" />
                <span>Control sharing</span>
            </a>
            <a v-if="!readOnly" class="dropdown-item" href="#" @click.prevent="onDelete">
                <span class="fa fa-trash fa-fw mr-1" />
                <span>Delete</span>
            </a>
        </div>
    </div>
</template>
