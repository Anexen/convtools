import random
import statistics

from operator import eq
import pytest
from collections import Counter

from convtools import conversion as c
from convtools.aggregations import MultiStatementReducer


class SumReducer1(MultiStatementReducer):
    reduce = ("%(result)s = {0} + ({1} or 1)",)
    default = int
    initial = int
    unconditional_init = True


class SumReducer2(MultiStatementReducer):
    reduce = ("%(result)s = {0} + ({1} or 2)",)
    default = 0
    initial = 0
    unconditional_init = True


class SumReducer3(MultiStatementReducer):
    reduce = ("%(result)s = {0} + ({1} or 3)",)
    initial = 0
    unconditional_init = True


class SumReducer4(MultiStatementReducer):
    prepare_first = ("%(result)s = {0}",)
    reduce = ("%(result)s = {0} + ({1} or 4)",)
    default = 0
    unconditional_init = True


class SumReducer5(MultiStatementReducer):
    reduce = ("%(result)s = {0} + ({1} or 5)",)
    default = 0
    unconditional_init = True


@pytest.fixture
def dict_series():
    return [
        {"name": "Nick", "value": 1},
        {"name": "Nick", "value": 2},
        {"name": "John", "value": 20},
        {"name": "John", "value": 21},
        {"name": "John", "value": 22},
    ]


@pytest.fixture
def series():
    random.seed(73)
    return [
        (random.randint(0, 100), random.randint(0, 10 ** 9))
        for _ in range(10000)
    ]


def weighted_average(samples):
    return


def test_multi_statement_reducers(dict_series):
    output = (
        c.group_by(c.item("name"))
        .aggregate(
            (
                c.item("name"),
                SumReducer1(c.item("value")),
                SumReducer2(c.item("value")),
                SumReducer3(c.item("value")),
                SumReducer4(c.item("value")),
                SumReducer5(c.item("value"), initial=5),
            )
        )
        .execute(dict_series, debug=True)
    )
    assert output == [("Nick", 3, 3, 3, 3, 8), ("John", 63, 63, 63, 63, 68)]

    with pytest.raises(ValueError):

        class SumReducer(MultiStatementReducer):
            reduce = ("%(result)s = {0} + ({1} or 4)",)
            default = 0
            unconditional_init = True

        SumReducer(c.item("value"))
    with pytest.raises(ValueError):

        class SumReducer(MultiStatementReducer):
            reduce = ("%(result)s = {0} + ({1} or 4)",)
            unconditional_init = True

        SumReducer(c.item("value"))


def test_custom_reduce():
    with pytest.raises(ValueError):
        c.reduce(lambda a, b: a + b, c.this())
    with pytest.raises(ValueError):
        c.reduce(lambda a, b: a + b, c.this(), default=0)


def test_legacy_dict_reduce_approach(dict_series):
    output = c.aggregate(
        c.reduce(
            c.ReduceFuncs.DictSum,
            (c.item("name"), c.item("value")),
        )
    ).execute(dict_series)
    assert output == {
        "Nick": 3,
        "John": 63,
    }
    with pytest.raises(ValueError):
        c.ReduceFuncs.DictSum(c.this(), c.this(), c.this())
    with pytest.raises(ValueError):
        c.ReduceFuncs.DictSum({c.this(), c.this()})


def test_reducer_reuse(dict_series):
    f = lambda a, b: a + b
    reducer = c.reduce(f, c.item("value"), initial=0)
    reducer2 = c.reduce(f, c.item("value"), initial=0)
    output = (
        c.group_by(c.item("name"))
        .aggregate(
            (
                c.item("name"),
                reducer + 10,
                reducer2 + 20,
            )
        )
        .execute(dict_series)
    )
    assert output == [
        ("Nick", 13, 23),
        ("John", 73, 83),
    ]


def test_blank_aggregate(series):
    assert eq(
        c.group_by(c.item(0)).aggregate(c.item(0)).execute(series),
        list({x[0]: 1 for x in series}),
    )


def test_average(series):
    assert eq(
        c.aggregate(c.ReduceFuncs.Average(c.item(1))).execute(series),
        statistics.mean(x[1] for x in series),
    )


def test_average_of_empty_collection():
    assert c.aggregate(c.ReduceFuncs.Average(c.item(1))).execute([]) is None


def test_weighted_average(series):
    assert eq(
        c.aggregate(c.ReduceFuncs.Average(c.item(0), c.item(1))).execute(
            series
        ),
        sum(v * w for v, w in series) / sum(x[1] for x in series),
    )


def test_mode(series):
    assert eq(
        c.aggregate(c.ReduceFuncs.Mode(c.item(0))).execute(series),
        statistics.mode(x[0] for x in series),
    )


@pytest.mark.parametrize("k", [1, 5, 10 ** 9])
def test_top_k(series, k):
    assert eq(
        c.aggregate(c.ReduceFuncs.TopK(k, c.item(1))).execute(series),
        [x[1] for x in Counter(x[1] for x in series).most_common(k)],
    )


@pytest.mark.parametrize("k", [0, -1])
def test_top_k_non_positive_int(k):
    with pytest.raises(ValueError):
        c.aggregate(c.ReduceFuncs.TopK(k, c.this())).execute([1, 2]),


@pytest.mark.parametrize("k", [c.item(1), "abc"])
def test_top_k_invalid_input(k):
    with pytest.raises(TypeError):
        c.aggregate(c.ReduceFuncs.TopK(k, c.this())).execute([1, 2]),


def test_median(series):
    assert eq(
        c.aggregate(c.ReduceFuncs.Median(c.item(1))).execute(series),
        statistics.median(x[1] for x in series),
    )