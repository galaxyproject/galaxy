import yaml


def main(trans, webhook):
    data = {}
    data['tools'] = []
    unique_tools = []

    tools = trans.app.toolbox.tools()

    for tool in tools:
        if tool[1].tool_shed_repository is not None:

            name = str(tool[1].tool_shed_repository.name)
            revision = str(
                tool[1].tool_shed_repository.installed_changeset_revision
            )

            if (name + revision) not in unique_tools:

                unique_tools.append(name + revision)

                data['tools'].append({
                    'name': name,
                    'owner': tool[1].tool_shed_repository.owner,
                    'tool_panel_section_label': tool[1].get_panel_section()[1],
                    'tool_shed_url': tool[1].tool_shed_repository.tool_shed,
                    'install_tool_dependencies': True,
                    'install_repository_dependencies': True,
                    'install_resolver_dependencies': True,
                    'revisions': [revision]
                })
                if tool[1].get_panel_section()[0]:
                    data['tools'][-1]['tool_panel_section_id'] = \
                        tool[1].get_panel_section()[0]

    return {'yaml': yaml.safe_dump(data, default_flow_style=False)}
