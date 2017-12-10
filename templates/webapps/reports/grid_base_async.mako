<%namespace name="grid_base" file="/webapps/reports/grid_base.mako" import="*" />

${init()}
${h.dumps( grid_base.get_grid_config() )}
