# Tool Shed Migration Notes

The Galaxy developer community has different intentions and ideas for the tool shed going forward including:

- a complete rewrite (https://github.com/hexylena/shed)
- merge the existing functionality that is needed into DockStore (https://dockstore.org/)
- a rewrite of Galaxy to just use GitHub directly (the Anton approach)
- spinning the codebase off as is (duplicating and freezing the Galaxy half) (https://github.com/galaxyproject/galaxy/pull/8830)
- spinning the code base while continuing reuse via Python packaging

There is largely agreement that the tool shed code is aging and if the UI should continue
to exist it should be rewritten. The ecosystem has evolved such that I think all parties would
also agree that all server access (by Galaxy or a new UI) should be via a tool shed API and should
be typed and well modelled.

This chart is meant to track what API endpoints are used where and how they are used to gauage
how conservative we should be in breaking backward compatiblity. This chart doesn't guarentee
endpoints will remain, will stay consistent, or even that a tool shed API will continue to exist.
It is just meant to track information and allow us to make clear choices. Nothing is scared here.

Things seemingly _NOT_ used by Galaxy, Planemo, or Ephemeris. These are easy candidates for
for deletion instead of writing new tests and modernizing the API.

- reset_metadata_on_repositories
- remove_repository_registry_entry
- get_installable_revisions
- The whole Groups API.
- The whole Repository Revisions API.

| api                                                                       | Galaxy                         | Planemo | Ephemeris | Pydantic or API tests | Used for TS Functional Testing | Notes                                                         |
| ------------------------------------------------------------------------- | ------------------------------ | ------- | --------- | --------------------- | ------------------------------ | ------------------------------------------------------------- | --------------------- |
| GET categories                                                            | ?                              | ?       | ?         | YES                   | NO                             | Easy to maintain/migrate                                      |
| POST categories                                                           | NO                             | NO      | NO        | YES                   | YES                            | Easy to maintain/migrate                                      |
| get_repository_revision_install_info                                      | YES                            |         |           |                       |                                | NO                                                            | Used by install code. |
| get_ordered_installable_revisions                                         | NO                             | NO      | YES       | YES                   | NO                             | used by complete_repo_information in ephemeris for shed_tools |
| reset_metadata_on_repository                                              | NO                             | NO      | NO        | YES                   | NO                             | Bjoern said it was a thing that is done via the UI still      |
| GET repositories/{repository_id}/metadata                                 | Yes (getRepository in client?) | NO?     | NO?       | YES                   | NO                             |                                                               |
| /github.com/galaxyproject/galaxy/pull/14672#pullrequestreview-1116016874) |
| repo search (Get repositories + q param)                                  | YES                            | NO      | NO        | YES                   | NO                             | Used by the Vue tool shed install interface.                  |
| repositories/{repository_id}/changeset_revision                           | NO                             | YES     | NO        | YES                   | NO                             |                                                               |
| POST repositories                                                         | NO                             | YES     | NO        | YES                   | NO                             |                                                               |
| GET repositories (without search query)                                   | ?                              | ?       | ?         | True                  | True                           |                                                               |
| GET /repositories/updates/                                                | YES                            | NO      | NO        | NO                    | YES                            |                                                               |
| GET/POST/DELETE repositories/{id}/admins                                  | NO                             | NO      | NO        | YES                   | YES                            | Needed for functional tests, should have a UI at some point   |

Research if searching by tool_ids is used with the repository index API.

Added in:

- https://github.com/galaxyproject/galaxy/pull/3626/files
- Likely no longer used?

## Legacy /repository/* endpoints required by Galaxy install client

Galaxy's install code (`lib/galaxy/tool_shed/galaxy_install/`) makes server-to-server HTTP
calls to the Tool Shed using `/repository/{action}` endpoints. These are **not** part of
the `/api/` surface but are critical for repository installation, update checking, and
dependency resolution.

These endpoints have been migrated from the WSGI `RepositoryController` to FastAPI in
`lib/tool_shed/webapp/api2/repository.py`, with business logic in
`lib/tool_shed/managers/repositories.py`. The URLs are unchanged so existing Galaxy
clients continue to work. Tests are in
`lib/tool_shed/test/functional/test_shed_galaxy_install_apis.py`.

| Endpoint                                        | Galaxy caller                                                  | Purpose                                              |
| ----------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------- |
| `/repository/get_ctx_rev`                        | `lib/galaxy/tool_shed/util/shed_util_common.py`                | Get hg ctx.rev() for a changeset during clone        |
| `/repository/get_changeset_revision_and_ctx_rev` | `lib/galaxy/tool_shed/galaxy_install/update_repository_manager.py` | Check for updates to installed repos             |
| `/repository/get_repository_dependencies`        | `lib/galaxy/tool_shed/galaxy_install/repository_dependencies/repository_dependency_manager.py` | Resolve repo dependencies during install |
| `/repository/get_required_repo_info_dict`        | `lib/galaxy/tool_shed/galaxy_install/repository_dependencies/repository_dependency_manager.py` | Get install info for dependency repos    |
| `/repository/next_installable_changeset_revision`| `lib/galaxy/tool_shed/util/repository_util.py`                 | Find next installable revision                       |
| `/repository/previous_changeset_revisions`       | `lib/galaxy/tool_shed/util/repository_util.py`                 | List changeset hashes for update range               |
| `/repository/updated_changeset_revisions`        | `lib/galaxy/tool_shed/util/metadata_util.py`                   | List revisions an installed repo can update to        |
| `/repository/get_repository_type`                | (not currently called but was available)                        | Return repository type string                        |
| `/repository/get_tool_dependencies`              | (not currently called but was available)                        | Return tool dependencies for a changeset             |
