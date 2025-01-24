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

Things seemingly *NOT* used by Galaxy, Planemo, or Ephemeris. These are easy candidates for 
for deletion instead of writing new tests and modernizing the API.

- reset_metadata_on_repositories
- remove_repository_registry_entry
- get_installable_revisions
- The whole Groups API.
- The whole Repository Revisions API.

| api | Galaxy | Planemo | Ephemeris | Pydantic or API tests | Used for TS Functional Testing | Notes |
| --- | ------ | ------- | --------- | --------------------- | ------------------------------ | ----- |
| GET categories | ? | ? | ? | YES | NO |  Easy to maintain/migrate |
| POST categories | NO | NO | NO | YES | YES | Easy to maintain/migrate |
| get_repository_revision_install_info | YES | | | | | NO | Used by install code. |
| get_ordered_installable_revisions | NO | NO | YES | YES | NO | used by complete_repo_information in ephemeris for shed_tools |
| reset_metadata_on_repository | NO | NO | NO | YES | NO | Bjoern said it was a thing that is done via the UI still |
| GET repositories/{repository_id}/metadata| Yes (getRepository in client?) | NO? | NO? | YES | NO | |
/github.com/galaxyproject/galaxy/pull/14672#pullrequestreview-1116016874) |
| repo search (Get repositories + q param) | YES | NO | NO | YES | NO | Used by the Vue tool shed install interface. |
| repositories/{repository_id}/changeset_revision | NO | YES | NO | YES | NO | |
| POST repositories | NO | YES | NO | YES | NO | |
| GET repositories (without search query) | ? | ? |? | True | True | |
| GET /repositories/updates/ | YES | NO | NO | NO | YES | |

Research if searching by tool_ids is used with the repository index API.

Added in:
- https://github.com/galaxyproject/galaxy/pull/3626/files
- Likely no longer used?
