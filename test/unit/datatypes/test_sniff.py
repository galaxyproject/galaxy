import tempfile

from galaxy.datatypes.sniff import convert_newlines_sep2tabs, sep2tabs


def assert_converts_to_1234_sep2tabs(content, line_ending="\n"):
    print("\r" in content)
    tf = tempfile.NamedTemporaryFile(delete=False, mode='w')
    tf.write(content)
    tf.close()
    rval = sep2tabs(tf.name, tmp_prefix="gxtest", tmp_dir=tempfile.gettempdir())
    assert rval == (2, None), rval
    assert '1\t2%s3\t4%s' % (line_ending, line_ending) == open(tf.name).read()


def assert_converts_to_1234_convert_sep2tabs(content, expected='1\t2\n3\t4\n', line_ending="\n"):
    print("\r" in content)
    tf = tempfile.NamedTemporaryFile(delete=False, mode='w')
    tf.write(content)
    tf.close()
    rval = convert_newlines_sep2tabs(tf.name, tmp_prefix="gxtest", tmp_dir=tempfile.gettempdir())
    assert rval == (2, None), rval
    assert expected == open(tf.name).read()


def test_sep2tabs():
    assert_converts_to_1234_sep2tabs("1 2\n3 4\n")
    assert_converts_to_1234_sep2tabs("1    2\n3    4\n")
    assert_converts_to_1234_sep2tabs("1\t2\n3\t4\n")
    assert_converts_to_1234_sep2tabs("1\t2\r3\t4\r", line_ending='\r')
    assert_converts_to_1234_sep2tabs("1\t2\r\n3\t4\r\n", line_ending='\r\n')


def test_convert_sep2tabs():
    assert_converts_to_1234_convert_sep2tabs("1 2\n3 4\n")
    assert_converts_to_1234_convert_sep2tabs("1    2\n3    4\n")
    assert_converts_to_1234_convert_sep2tabs("1\t2\n3\t4\n")
    assert_converts_to_1234_convert_sep2tabs("1\t2\r3\t4\r")
    assert_converts_to_1234_convert_sep2tabs("1\t2\r\n3\t4\r\n")
    assert_converts_to_1234_convert_sep2tabs("1    2\r\n3       4\r\n")
    assert_converts_to_1234_convert_sep2tabs("1 2     \n3 4 \n", expected='1\t2\t\n3\t4\t\n')
