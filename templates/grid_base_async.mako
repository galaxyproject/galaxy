<%namespace name="grid_base" file="./grid_base.mako" import="*" />

${init()}
${h.to_json_string( grid_base.grid_config )}