import re
from collections import Counter
from glob import glob
from itertools import chain

import pytest

from convtools import conversion as c


TOP_N = 50
WORD_PATTERN = re.compile(r"\w+")


@pytest.fixture
def input_files():
    # return [
    #     "tests/data/war-and-peace.txt",
    #     "tests/data/crime-and-punishment.txt",
    # ]
    return glob("**/*.py", recursive=True)


def read_lines(filename):
    with open(filename) as f:
        for line in f:
            yield line


def generate_word_count_conversion():
    flatten = c.call_func(chain.from_iterable, c.this())

    extract_lines = c.generator_comp(c.call_func(read_lines, c.this()))

    split_words = (
        c.naive(WORD_PATTERN)
        .call_method("findall", c.this())
        .pipe(c.generator_comp(c.this().call_method("lower")))
    )

    vectorized_split_words = c.generator_comp(c.this().pipe(split_words))

    dict_word_to_count = c.aggregate(
        c.ReduceFuncs.DictCount(c.this(), c.this(), default=dict)
    )

    take_top_n = (
        c.this()
        .call_method("items")
        .sort(key=lambda t: t[1], reverse=True)
        .pipe(c.this()[: c.input_arg("top_n")])
        .as_type(dict)
    )

    pipeline = (
        extract_lines.pipe(flatten)
        .pipe(vectorized_split_words)
        .pipe(flatten)
        .pipe(dict_word_to_count)
        .pipe(
            c.if_(
                c.input_arg("top_n").is_not(None),
                c.this().pipe(take_top_n),
            )
        )
    )

    # Define the resulting converter function signature.  In fact this
    # isn't necessary if you don't need to specify default values
    return pipeline.gen_converter(signature="data_, top_n=None")


def naive_word_count(input_data, top_n=None):
    result = Counter()

    for filename in input_data:
        for line in read_lines(filename):
            result.update(map(str.lower, WORD_PATTERN.findall(line)))

    return dict(result.most_common(top_n) if top_n else result)


@pytest.mark.bench
def test_convtools_word_count(benchmark, input_files):

    pipeline = generate_word_count_conversion()
    result = benchmark(pipeline, input_files, TOP_N)

    # Extra code, to verify that the run completed correctly.
    # Fast functions are no good if they return incorrect results :-)
    assert result == naive_word_count(input_files, TOP_N)


@pytest.mark.bench
def test_naive_word_count(benchmark, input_files):
    result = benchmark(naive_word_count, input_files, TOP_N)

    assert len(result) == TOP_N
