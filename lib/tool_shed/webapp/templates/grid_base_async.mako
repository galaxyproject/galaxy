<%namespace name="grid_base" file="/legacy/grid_base.mako" import="*" />

${init()}
${h.dumps( grid_base.get_grid_config() )}
