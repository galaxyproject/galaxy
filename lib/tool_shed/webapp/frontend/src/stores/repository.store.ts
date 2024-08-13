import { defineStore } from "pinia"

import { ToolShedApi, components } from "@/schema"
import { notifyOnCatch } from "@/util"

function fetchRepositoryPermissions(repositoryId: string) {
    return ToolShedApi().GET("/api/repositories/{encoded_repository_id}/permissions", {
        params: {
            path: { encoded_repository_id: repositoryId },
        },
    })
}

type DetailedRepository = components["schemas"]["DetailedRepository"]
type InstallInfo = components["schemas"]["InstallInfo"]
type RepositoryMetadata = components["schemas"]["RepositoryMetadata"]
type RepositoryPermissions = components["schemas"]["RepositoryPermissions"]

export const useRepositoryStore = defineStore({
    id: "repository",
    state: () => ({
        repositoryId: null as string | null,
        repository: null as DetailedRepository | null,
        repositoryMetadata: null as RepositoryMetadata | null,
        repositoryInstallInfo: null as InstallInfo | null,
        repositoryPermissions: null as RepositoryPermissions | null,
        loading: true as boolean,
        empty: false as boolean,
    }),
    actions: {
        async allowPush(username: string) {
            try {
                if (this.repositoryId == null) {
                    throw Error("Logic problem in repository store")
                }
                const params = {
                    encoded_repository_id: this.repositoryId,
                    username: username,
                }
                await ToolShedApi().POST("/api/repositories/{encoded_repository_id}/allow_push/{username}", {
                    params: { path: params },
                })
                const { data: _repositoryPermissions } = await fetchRepositoryPermissions(this.repositoryId)
                this.repositoryPermissions = _repositoryPermissions ?? null
            } catch (e) {
                notifyOnCatch(e)
            }
        },
        async disallowPush(username: string) {
            try {
                if (this.repositoryId == null) {
                    throw Error("Logic problem in repository store")
                }
                const params = {
                    encoded_repository_id: this.repositoryId,
                    username: username,
                }
                await ToolShedApi().DELETE("/api/repositories/{encoded_repository_id}/allow_push/{username}", {
                    params: { path: params },
                })
                const { data: _repositoryPermissions } = await fetchRepositoryPermissions(this.repositoryId)
                this.repositoryPermissions = _repositoryPermissions ?? null
            } catch (e) {
                notifyOnCatch(e)
            }
        },
        async setId(repositoryId: string) {
            this.repositoryId = repositoryId
            this.refresh()
        },
        async refresh() {
            if (!this.repositoryId) {
                return
            }
            this.loading = true
            const params = { encoded_repository_id: this.repositoryId }
            try {
                const [{ data: repository }, { data: repositoryMetadata }] = await Promise.all([
                    ToolShedApi().GET("/api/repositories/{encoded_repository_id}", { params: { path: params } }),
                    ToolShedApi().GET("/api_internal/repositories/{encoded_repository_id}/metadata", {
                        params: { path: params, query: { downloadable_only: false } },
                    }),
                ])
                this.repository = repository ?? null
                this.repositoryMetadata = repositoryMetadata ?? null

                let repositoryPermissions = {
                    can_manage: false,
                    can_push: false,
                    allow_push: [] as string[],
                }
                try {
                    const { data: _repositoryPermissions } = await fetchRepositoryPermissions(this.repositoryId)
                    repositoryPermissions = _repositoryPermissions ?? repositoryPermissions
                    this.repositoryPermissions = repositoryPermissions
                } catch (e) {
                    // console.log(e)
                }
                const latestMetadata = Object.values(repositoryMetadata ?? {})[0]
                if (!latestMetadata || !repository) {
                    this.empty = true
                } else {
                    if (this.empty) {
                        this.empty = false
                    }
                    const installParams = {
                        name: repository.name,
                        owner: repository.owner,
                        changeset_revision: latestMetadata.changeset_revision,
                    }
                    const { data: repositoryInstallInfo } = await ToolShedApi().GET("/api/repositories/install_info", {
                        params: { query: installParams },
                    })
                    this.repositoryInstallInfo = repositoryInstallInfo ?? null
                }
            } catch (e) {
                notifyOnCatch(e)
            } finally {
                this.loading = false
            }
        },
    },
})
