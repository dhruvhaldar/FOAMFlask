import timeit

_DANGEROUS_CHARS_SET = frozenset([
    ";", "&", "|", "`", "$", "(", ")", "<", ">", '"', "'",
    "*", "?", "[", "]", "~", "!", "\n", "\r", "{", "}", "\\", "#"
])

def test_set_disjoint(cmd):
    return not set(cmd).isdisjoint(_DANGEROUS_CHARS_SET)

def test_any(cmd):
    return any(c in _DANGEROUS_CHARS_SET for c in cmd)

cmd_safe = "blockMesh -dict system/blockMeshDict " * 5
cmd_unsafe_early = "echo hello && " + "blockMesh " * 5
cmd_unsafe_late = "blockMesh " * 5 + " && echo hello"

print("Safe command:")
print("set_disjoint:", timeit.timeit(lambda: test_set_disjoint(cmd_safe), number=100000))
print("any:", timeit.timeit(lambda: test_any(cmd_safe), number=100000))

print("\nUnsafe early:")
print("set_disjoint:", timeit.timeit(lambda: test_set_disjoint(cmd_unsafe_early), number=100000))
print("any:", timeit.timeit(lambda: test_any(cmd_unsafe_early), number=100000))

print("\nUnsafe late:")
print("set_disjoint:", timeit.timeit(lambda: test_set_disjoint(cmd_unsafe_late), number=100000))
print("any:", timeit.timeit(lambda: test_any(cmd_unsafe_late), number=100000))
