import yaml


def main(trans, webhook, params):
    data = {}
    data['tools'] = []
    unique_tools = []

    tools = trans.app.toolbox.tools()

    for tool in tools:

        try:
            ts_data = tool[1].tool_shed_repository.to_dict()
            panel = tool[1].get_panel_section()
        except AttributeError:
            continue

        if (ts_data['name'] + ts_data['installed_changeset_revision'] not in
                unique_tools):

            unique_tools.append(
                ts_data['name'] + ts_data['installed_changeset_revision']
            )

            data['tools'].append({
                'name': ts_data['name'],
                'owner': ts_data['owner'],
                'tool_panel_section_label': panel[1],
                'tool_shed_url': ts_data['tool_shed'],
                'install_tool_dependencies': True,
                'install_repository_dependencies': True,
                'install_resolver_dependencies': True,
                'revisions': [ts_data['installed_changeset_revision']]
            })
            if panel[0]:
                data['tools'][-1]['tool_panel_section_id'] = panel[0]

    return {'yaml': yaml.safe_dump(data, default_flow_style=False)}
