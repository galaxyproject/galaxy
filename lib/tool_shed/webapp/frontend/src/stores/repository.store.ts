import { defineStore } from "pinia"

import { fetcher, components } from "@/schema"
const repositoryFetcher = fetcher.path("/api/repositories/{encoded_repository_id}").method("get").create()
const repositoryMetadataFetcher = fetcher
    .path("/api_internal/repositories/{encoded_repository_id}/metadata")
    .method("get")
    .create()
const repositoryPermissionsFetcher = fetcher
    .path("/api/repositories/{encoded_repository_id}/permissions")
    .method("get")
    .create()
const repositoryPermissionsAdder = fetcher
    .path("/api/repositories/{encoded_repository_id}/allow_push/{username}")
    .method("post")
    .create()
const repositoryPermissionsRemover = fetcher
    .path("/api/repositories/{encoded_repository_id}/allow_push/{username}")
    .method("delete")
    .create()
const repositoryInstallInfoFetcher = fetcher.path("/api/repositories/install_info").method("get").create()

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
            if (this.repositoryId == null) {
                throw Error("Logic problem in repository store")
            }
            const params = {
                encoded_repository_id: this.repositoryId,
                username: username,
            }
            await repositoryPermissionsAdder(params)
            const { data: _repositoryPermissions } = await repositoryPermissionsFetcher(params)
            this.repositoryPermissions = _repositoryPermissions
        },
        async disallowPush(username: string) {
            if (this.repositoryId == null) {
                throw Error("Logic problem in repository store")
            }
            const params = {
                encoded_repository_id: this.repositoryId,
                username: username,
            }
            await repositoryPermissionsRemover(params)
            const { data: _repositoryPermissions } = await repositoryPermissionsFetcher(params)
            this.repositoryPermissions = _repositoryPermissions
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
            const metadataParams = { encoded_repository_id: this.repositoryId, downloadable_only: false }
            const [{ data: repository }, { data: repositoryMetadata }] = await Promise.all([
                repositoryFetcher(params),
                repositoryMetadataFetcher(metadataParams),
            ])
            this.repository = repository
            this.repositoryMetadata = repositoryMetadata
            let repositoryPermissions = {
                can_manage: false,
                can_push: false,
                allow_push: [] as string[],
            }
            try {
                const { data: _repositoryPermissions } = await repositoryPermissionsFetcher(params)
                repositoryPermissions = _repositoryPermissions
                this.repositoryPermissions = repositoryPermissions
            } catch (e) {
                // console.log(e)
            }
            const latestMetadata = Object.values(repositoryMetadata)[0]
            if (!latestMetadata) {
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
                const { data: repositoryInstallInfo } = await repositoryInstallInfoFetcher(installParams)
                this.repositoryInstallInfo = repositoryInstallInfo
            }
            this.loading = false
        },
    },
})
