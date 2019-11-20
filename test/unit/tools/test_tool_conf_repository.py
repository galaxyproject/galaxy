def test_tool_conf_repository_get_tool_relative_path(tool_conf_repos):
    tool_conf_repo = tool_conf_repos[0]
    assert tool_conf_repo.get_tool_relative_path() == (tool_conf_repo.tool_path, tool_conf_repo.repository_path)
