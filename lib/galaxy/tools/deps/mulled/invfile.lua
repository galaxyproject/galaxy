-- http://stackoverflow.com/questions/19262761/lua-need-to-split-at-comma/19263313#19263313
function string:split( inSplitPattern, outResults )
  if not outResults then
    outResults = { }
  end
  local theStart = 1
  local theSplitStart, theSplitEnd = string.find( self, inSplitPattern, theStart )
  while theSplitStart do
    table.insert( outResults, string.sub( self, theStart, theSplitStart-1 ) )
    theStart = theSplitEnd + 1
    theSplitStart, theSplitEnd = string.find( self, inSplitPattern, theStart )
  end
  table.insert( outResults, string.sub( self, theStart ) )
  return outResults
end

local repo = VAR.REPO

local channel_args = ''
local channels = VAR.CHANNELS:split(",")
for i = 1, #channels do
    channel_args = channel_args .. " -c " .. channels[i]
end

local target_args = ''
local targets = VAR.TARGETS:split(",")
for i = 1, #targets do
    target_args = target_args .. " " .. targets[i]
end

local bind_args = {}
local binds_table = VAR.BINDS:split(",")
for i = 1, #binds_table do
    table.insert(bind_args, binds_table[i])
end

inv.task('build')
    .using('continuumio/miniconda:latest')
        .withHostConfig({binds = {"build:/data"}})
        .run('rm', '-rf', '/data/dist')
    .using('continuumio/miniconda:latest')
        .withHostConfig({binds = bind_args})
        .run('/bin/sh', '-c', 'conda install '
            .. channel_args .. ' '
            .. target_args
            .. ' -p /usr/local --copy --yes --quiet')
    .wrap('build/dist')
        .at('/usr/local')
        .inImage('bgruening/busybox-bash:0.1')
        .as(repo)

inv.task('test')
    .using(repo)
    .withConfig({entrypoint = {'/bin/sh', '-c'}})
    .run(VAR.TEST)

inv.task('push')
    .push(repo)

inv.task('build-and-test')
    .runTask('build')
    .runTask('test')

inv.task('all')
    .runTask('build')
    .runTask('test')
    .runTask('push')
