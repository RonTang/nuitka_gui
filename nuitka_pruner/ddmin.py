def split_chunks(values, count):
    values = sorted(values)
    count = min(max(2, count), len(values))
    return [set(values[index::count]) for index in range(count)]


def ddmin(keep, test_keep, n=2, on_progress=None):
    """最小化仍需保留的模块；test_keep 返回冒烟测试是否通过。"""
    keep = set(keep)
    if not keep:
        return set()
    n = min(max(2, n), len(keep))
    if on_progress:
        on_progress(n, len(keep))
    chunks = split_chunks(keep, n)

    for chunk in chunks:
        complement = keep - chunk
        if test_keep(complement):
            return ddmin(complement, test_keep, 2, on_progress=on_progress)

    if n > 2:
        for chunk in chunks:
            if test_keep(chunk):
                return ddmin(
                    chunk, test_keep, max(n - 1, 2), on_progress=on_progress
                )

    if n < len(keep):
        return ddmin(
            keep, test_keep, min(len(keep), n * 2), on_progress=on_progress
        )
    return keep
