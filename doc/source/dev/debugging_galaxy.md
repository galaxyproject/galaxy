
# Debugging Galaxy

## Debugging Galaxy in VS Code 

The following instructions assume that you have cloned your Galaxy fork into the
`~/galaxy` directory and have created a VS Code workspace per instructions
[here](./debugging_tests.md).  Additionally, we assume you have configured
Galaxy and are using `~/galaxy/config/galaxy.yml` as your galaxy configuration
file (so, not the default .sample). If you are still using the default
configuration, simply `cp config/galaxy.yml.sample config/galaxy.yml` and it
should work fine.


1. Add the following code snippet to `~/galaxy/.vscode/launch.json` (create the file if it does not already exist)
    ``` 
    {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Python: Current File (Integrated Terminal)",
                "type": "python",
                "request": "launch",
                "program": "${file}",
                "console": "integratedTerminal"
            },
            {
                "name": "GalaxyFastAPI uvicorn",
                "type": "python",
                "request": "launch",
                "module": "uvicorn",
                "args": ["--app-dir", "lib",  "--factory", "galaxy.webapps.galaxy.fast_factory:factory"],
                "env": {
                    "GALAXY_CONFIG_FILE": "${workspaceFolder}/config/galaxy.yml"
                }
            },
        ]
    }

    ```
2. Re-start VS Code
3. Add a breakpoint somewhere in your code
4. Select Run and Debug on Activity Bar, on the far left hand side. In the RUN AND DEBUG drop down, select `GalaxyFastAPI uvicorn`, and click the Start Debugging button (green arrow)
5. Galaxy should stop right on the break point you added.
6. Enjoy your debugging session :-)
