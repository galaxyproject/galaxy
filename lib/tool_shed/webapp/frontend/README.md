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
