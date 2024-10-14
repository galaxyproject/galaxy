# Tool Shed 2.0 client

The following assumes `npx` is installed, but equivalent npm commands should work too.

To start a HMR dev server run

```shell
npx vite dev
```

Note that you will need to start the Tool Shed backend from the galaxy root directory:

```shell
TOOL_SHED_API_VERSION=v2 ./run_tool_shed.sh
```

If you want to target an external V2 tool shed API run

```shell
TOOL_SHED_URL=https://testtoolshed.g2.bx.psu.edu CHANGE_ORIGIN=true npx vite dev
```
