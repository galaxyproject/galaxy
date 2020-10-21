
# Debugging Galaxy

## Debugging Galaxy in VS Code 

The following instructions assume that you have cloned your Galaxy fork into the `~/galaxy` directory and have created a VS Code workspace per instructions [here](./debugging_tests.md)

1. Download this [ini](https://gist.github.com/kxk302/1b996e3359513e1f40d91ffbc82559c8) file and and save it as ~/galaxy/config/galaxy.ini.old
2. Add the following code snippet to `~/galaxy/.vscode/launch.json` (create the file if it does not already exist)
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
                "name": "Galaxy debug",
                "type": "python",
                "request": "launch",
                "program": "${workspaceFolder}/scripts/paster.py",
                "args": [
                    "serve",
                    "config/galaxy.ini.old",
                    "--log-file",
                    "galaxy.log",
                ],
            }
        ]
    }

    ```
3. Re-start VS Code
4. Add a breakpoint somewhere in your code
5. Select Run and Debug on Activity Bar, on the far left hand side. In the RUN AND DEBUG drop down, select Galaxy debug (galaxy), and click the Start Debugging button (green arrow)
6. Galaxy should stop right on the break point you added.
7. Enjoy your debugging session :-)
