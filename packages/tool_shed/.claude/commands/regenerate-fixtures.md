Regenerate API test fixtures for MetadataInspector frontend components.

# Command

Run from `packages/tool_shed`:
```bash
TOOL_SHED_FIXTURE_OUTPUT_DIR=tool_shed/webapp/frontend/src/components/MetadataInspector/__fixtures__ \
TOOL_SHED_API_VERSION=v2 \
uv run pytest tool_shed/test/functional/test_shed_repositories.py::TestShedRepositoriesApi::test_generate_frontend_fixtures -v &&
cd tool_shed/webapp/frontend && npm run format
```



# Generated files

- `repository_metadata_column_maker.json` - Multi-revision repo with tools (RepositoryMetadata)
- `repository_metadata_bismark.json` - Repo with invalid_tools (RepositoryMetadata)
- `reset_metadata_preview.json` - Dry-run reset response (ResetMetadataOnRepositoryResponse)
- `reset_metadata_applied.json` - Applied reset response (ResetMetadataOnRepositoryResponse)

# When to regenerate

- After schema changes to RepositoryMetadata or related types
- After changes to reset_metadata API response structure
- After fixing bugs in changeset_details logging (e.g., duplicate entries, missing initial changeset)
