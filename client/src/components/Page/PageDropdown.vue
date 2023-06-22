<script setup lang="ts">
import _l from "@/utils/localization";
import { useRouter } from "vue-router/composables";
import { computed, unref } from "vue";
import { deletePage } from "./services";
import { storeToRefs } from "pinia";
import { useUserStore } from "@/stores/userStore";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";

const router = useRouter();
library.add(faCaretDown);

interface Page {
    id: string;
    shared?: Boolean;
    title?: string;
    description?: string;
}
interface PageDropdownProps {
    page: Page;
    published?: Boolean;
}

const props = defineProps<PageDropdownProps>();
const { isAnonymous } = storeToRefs(useUserStore());

const emit = defineEmits(["onRemove", "onSuccess", "onError"]);

const urlView = computed(() => `/published/page?id=${props.page.id}`);
const urlEdit = computed(() => `/pages/editor?id=${props.page.id}`);
const urlEditAttributes = computed(() => `/pages/edit?id=${props.page.id}`);
const urlShare = computed(() => `/pages/sharing?id=${props.page.id}`);
const readOnly = computed(() => props.page.shared || props.published || unref(isAnonymous));

function onDelete(page_id: string) {
    deletePage(page_id)
        .then((response) => {
            emit("onRemove", page_id);
            emit("onSuccess");
        })
        .catch((error) => {
            emit("onError", error);
        });
}

function pushUrl(url: string) {
    router.push(url);
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
            <font-awesome-icon icon="caret-down" class="fa-lg" />
            <span class="page-title">{{ props.page.title }}</span>
        </b-link>
        <p v-if="props.page.description">{{ props.page.description }}</p>
        <div class="dropdown-menu" aria-labelledby="page-dropdown">
            <a class="dropdown-item dropdown-item-view" href="javascript:void(0)" @click="pushUrl(urlView)">
                <span class="fa fa-eye fa-fw mr-1" />
                <span>View</span>
            </a>
            <a
                v-if="!readOnly"
                class="dropdown-item dropdown-item-edit"
                href="javascript:void(0)"
                @click="pushUrl(urlEdit)">
                <span class="fa fa-edit fa-fw mr-1" />
                <span>Edit content</span>
            </a>
            <a
                v-if="!readOnly"
                class="dropdown-item dropdown-item-attributes"
                href="javascript:void(0)"
                @click="pushUrl(urlEditAttributes)">
                <span class="fa fa-pencil fa-fw mr-1" />
                <span>Edit attributes</span>
            </a>
            <a
                v-if="!readOnly"
                class="dropdown-item dropdown-item-share"
                href="javascript:void(0)"
                @click="pushUrl(urlShare)">
                <span class="fa fa-share-alt fa-fw mr-1" />
                <span>Control sharing</span>
            </a>
            <a
                v-if="!readOnly"
                v-b-modal="`delete-page-modal-${props.page.id}`"
                class="dropdown-item dropdown-item-delete">
                <span class="fa fa-trash fa-fw mr-1" />
                <span>Delete</span>
            </a>
            <b-modal
                :id="`delete-page-modal-${props.page.id}`"
                hide-backdrop
                title="Confirm page deletion"
                title-tag="h2"
                @ok="onDelete(props.page.id)">
                <p v-localize>Really delete the page titled: "{{ props.page.title }}"?</p>
            </b-modal>
        </div>
    </div>
</template>
