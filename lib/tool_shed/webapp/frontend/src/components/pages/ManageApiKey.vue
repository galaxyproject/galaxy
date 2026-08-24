<script setup lang="ts">
import { GButton } from "@galaxyproject/galaxy-ui"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCopy, faTrash, faArrowsRotate } from "@fortawesome/free-solid-svg-icons"
import { ref, computed } from "vue"
import PageContainer from "@/components/PageContainer.vue"
import { ToolShedApi } from "@/schema"
import { notify, copyAndNotify, notifyOnCatch, errorMessageAsString } from "@/util"
import ConfigFileContents from "@/components/ConfigFileContents.vue"

const apiKey = ref<string | null>(null)
const planemoConfig = computed(
    () =>
        `sheds:
  toolshed:
    key: ${apiKey.value}`,
)

async function copyKey() {
    if (apiKey.value) {
        copyAndNotify(apiKey.value, "API key copied to your clipboard")
    }
}

const params = { encoded_user_id: "current" }

async function init() {
    try {
        const { data } = await ToolShedApi().GET("/api/users/{encoded_user_id}/api_key", {
            params: {
                path: params,
            },
        })
        apiKey.value = data ?? null
    } catch (e) {
        notifyOnCatch(new Error(`Error fetching API key: ${errorMessageAsString(e)}`))
    }
}

async function deleteKey() {
    try {
        await ToolShedApi().DELETE("/api/users/{encoded_user_id}/api_key", {
            params: {
                path: params,
            },
        })

        apiKey.value = null
        notify("API key deactivated")
    } catch (e) {
        notifyOnCatch(new Error(`Error deactivating API key: ${errorMessageAsString(e)}`))
    }
}

async function recreateKey() {
    try {
        const { data } = await ToolShedApi().POST("/api/users/{encoded_user_id}/api_key", {
            params: {
                path: params,
            },
        })

        if (data) {
            apiKey.value = data
            notify("Re-generated API key")
        }
    } catch (e) {
        notifyOnCatch(new Error(`Error re-generating API key: ${errorMessageAsString(e)}`))
    }
}

void init()
</script>
<template>
    <page-container>
        Your API Key.
        <div>
            <q-input class="q-pa-lg" v-model="apiKey" readonly filled style="max-width: 450px">
                <template #append>
                    <GButton icon-only transparent aria-label="Copy API key" @click="copyKey">
                        <FontAwesomeIcon :icon="faCopy" />
                    </GButton>
                    <GButton icon-only transparent aria-label="Deactivate API key" @click="deleteKey">
                        <FontAwesomeIcon :icon="faTrash" />
                    </GButton>
                    <GButton icon-only transparent aria-label="Regenerate API key" @click="recreateKey">
                        <FontAwesomeIcon :icon="faArrowsRotate" />
                    </GButton>
                </template>
            </q-input>
        </div>
        <p>
            This API key will allow you to access the Tool Shed via its web API. Please note that this key acts as an
            alternate means to access your account and should be treated with the same care as your login password.
        </p>
        <p>
            Add the following block to your Planemo configuration file (typically) found in
            <code>~/.planemo.yml</code> in your
        </p>
        <config-file-contents name=".planemo.yml" :contents="planemoConfig" what="Planemo configuration" />
    </page-container>
</template>
