# Debugging Galaxy Tests

## Debugging Galaxy unit & integration tests in VS code 

The following instructions assume that you have cloned your Galaxy fork into ~/galaxy directory.

1. Start VS Code
2. Create a VS Code workspace by selecting 'File -> Add Folder to Workspace...' from menu and adding the `~/galaxy` directory
3. Optionally, save the workspace by selecting 'File -> Save Workspace As...' and save as 'galaxy.code-workspace' in the `~/galaxy` directory 
2. Add the following snippet to `~/galaxy/.vscode/settings.json` (create the file if it does not already exist)
    ```
    {
        "python.testing.unittestEnabled": false,
        "python.testing.nosetestsEnabled": false,
        "python.testing.pytestEnabled": true,
        "python.testing.pytestArgs": [
            "test/",
            "--ignore=test/shed_functional/",
            "--ignore=test/functional",
            "--ignore=test/unit/shed_unit/test_shed_index.py",
            "packages/test_api/"
        ],
        "python.pythonPath": ".venv/bin/python3",
        "pythonTestExplorer.testFramework": "pytest",
    }
    ```
3. Re-start VS Code
4. Select Test on Activity Bar, on the far left hand side. You should see unit and integration tests under 'Python' (as shown in the image below). It may take a few seconds for the tests to load up. If they do not, click the 'Discover Tests' icon and wait for the tests to load.  
![VS Code Tests](tests.png) 
5. Expand integration/unit tests, select a test to display its source code in editor, add a breakpoint, and start the debugger by clicking on the debug icon (next to test name)
6. Enjoy your debugging session :-)
