# Tool Shed 2.0 client

You will need to start the Tool Shed backend from the galaxy root directory.
This is required if you want to develop against a local tool shed, and if you
plan to make changes to the graphql queries if you want to target a remote tool shed.

```shell
TOOL_SHED_API_VERSION=v2 ./run_tool_shed.sh
```

Start the HMR dev server **and** the graphql dev server

```shell
yarn run dev-all
```

If you want to target an external V2 tool shed API run

```shell
TOOL_SHED_URL=https://testtoolshed.g2.bx.psu.edu CHANGE_ORIGIN=true yarn vite dev
```

Note that you still need a local backend to generate the graphql schema.

To run a local toolshed patched for rapid bootstrapping and in local Vite dev server mode
the following command should work.

```shell
TOOL_SHED_CONFIG_OVERRIDE_BOOTSTRAP_ADMIN_API_KEY=tsadminkey TOOL_SHED_CONFIG_CONFIG_HG_FOR_DEV=1 TOOL_SHED_VITE_PORT=4040 TOOL_SHED_API_VERSION=v2 ./run_tool_shed.sh
```