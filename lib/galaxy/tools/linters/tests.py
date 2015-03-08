

# Misspelled so as not be picked up by nosetests.
def lint_tsts(tool_xml, lint_ctx):
    tests = tool_xml.findall("./tests/test")
    if not tests:
        lint_ctx.warn("No tests found, most tools should define test cases.")

    num_valid_tests = 0
    for test in tests:
        outputs = test.findall("output")
        if not outputs:
            lint_ctx.warn("No outputs defined for tests, this test is likely invalid.")
        else:
            num_valid_tests += 1

    if num_valid_tests:
        lint_ctx.valid("%d test(s) found.", num_valid_tests)
    else:
        lint_ctx.warn("No valid test(s) found.")
