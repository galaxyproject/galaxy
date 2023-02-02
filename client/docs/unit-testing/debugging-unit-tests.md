### ...in VSCode

There's a bunch of "how to debug javascript in vscode" cookbooks out there for the googling, but
most of them don't bother explaining all the gotchas and what each of the cryptic configuration
parameters actually does.

I've gone ahead and annotated all the options, hopefully this will save some time, at least until VS
code updates its test extensions again.

#### To debug a single Jest test:

1. Open a jest test (a file that ends with \*.test.js)

1. Make sure the test file is selected, especially if you have multiple files open. This process
   will fail confusingly and without obvious error if you have not launched the debugger with the
   actual Jest test file selected, and it's easy to accidentally click into another file if you've
   got a dozen open.

1. Place a breakpoint in the margin of the file. You can place breakpoints anywhere in your source,
   but you must launch the debugger while the jest file is selected because that is where jest and
   webpack will start compiling. Alternatively, you can manually override the selected file in the
   configuration definition, like if you're testing the same file over and over again and don't want
   to worry about selecting it.

1. Update your .vscode/launch.json file to include the following launch configuration. If you don't
   have a .vscode folder, you can just make one, but my experience is this all works better if you
   have explicitly saved your VSCode project into a workspace rather than just using "code ." from a
   terminal. Doing so will have initialized the .vscode folder already.

1. Click on the "Run and Debug" tab from the vscode icons on the left and choose the sample launch
   configuration (defined below) from the dropdown "run and debug". Or just hit F5.

1. Wait a bit, for webpack to compile everything, eventually you should be able to hover over
   variables near your breakpoint and see their values in the "Variables" section of the Run and
   Debug pane.

```json
// sample launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "node",
            "name": "debug selected jest test",
            "request": "launch",

            // launches version of jest from inside the node_modules
            // this means you need to have run yarn first
            "program": "${workspaceFolder}/client/node_modules/jest/bin/jest",
            "args": [
                // Alias -i.
                // Normally jest opens up a bunch of workers to run all your tests faster
                // but we don't want that right now.
                "--runInBand",

                // finds jest config
                "--config",
                "${workspaceFolder}/client/tests/jest/jest.config.js",

                // This is how vscode references the currently selected file
                "${file}"
            ],
            "cwd": "${workspaceFolder}/client",

            // opens jest output in integrated terminal
            "console": "integratedTerminal",

            // allows you to place breakpoints right in vscode's gutter
            "disableOptimisticBPs": true
        }
    ]
}
```
