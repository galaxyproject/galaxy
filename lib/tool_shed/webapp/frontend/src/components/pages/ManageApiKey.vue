<script setup lang="ts">
import { ref, computed } from "vue"
import PageContainer from "@/components/PageContainer.vue"
import { fetcher } from "@/schema"
import { notify, copyAndNotify, notifyOnCatch } from "@/util"
import ConfigFileContents from "@/components/ConfigFileContents.vue"

const apiKeyFetcher = fetcher.path("/api/users/{encoded_user_id}/api_key").method("get").create()
const deleteKeyFetcher = fetcher.path("/api/users/{encoded_user_id}/api_key").method("delete").create()
const recreateKeyFetcher = fetcher.path("/api/users/{encoded_user_id}/api_key").method("post").create()

const apiKey = ref(null as string | null)
const planemoConfig = computed(
    () =>
        `sheds:
  toolshed:
    key: ${apiKey.value}`
)

async function copyKey() {
    if (apiKey.value) {
        copyAndNotify(apiKey.value, "API key copied to your clipboard")
    }
}

const params = { encoded_user_id: "current" }

async function init() {
    apiKeyFetcher(params)
        .then(({ data }) => {
            apiKey.value = data
        })
        .catch(notifyOnCatch)
}

async function deleteKey() {
    deleteKeyFetcher(params)
        .then(() => {
            apiKey.value = null
            notify("API key deactivated")
        })
        .catch(notifyOnCatch)
}

async function recreateKey() {
    recreateKeyFetcher(params)
        .then(({ data }) => {
            apiKey.value = data
            notify("Re-generated API key")
        })
        .catch(notifyOnCatch)
}

void init()
</script>
<template>
    <page-container>
        Your API Key.
        <div>
            <q-input class="q-pa-lg" v-model="apiKey" readonly filled style="max-width: 450px">
                <template #append>
                    <q-avatar>
                        <q-btn flat dense icon="content_copy" @click="copyKey" />
                    </q-avatar>
                    <q-avatar>
                        <q-btn flat dense icon="delete" @click="deleteKey" />
                    </q-avatar>
                    <q-avatar>
                        <q-btn flat dense icon="refresh" @click="recreateKey" />
                    </q-avatar>
                </template>
            </q-input>
        </div>
        <p>
            This API key will allow you to access the Tool Shed via its web API. Please note that this key acts as an
            alternate means to access your account and should be treated with the same care as your login password.
        </p>
        <p>
            Add the following block to your Planemo configuration file (typically found in
            <code>~/.planemo.yml</code> in your
        </p>
        <config-file-contents name=".planemo.yml" :contents="planemoConfig" what="Planemo configuration" />
    </page-container>
</template>
