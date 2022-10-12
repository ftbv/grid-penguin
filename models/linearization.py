# Standalone functions to linearize non-linear functions in the cvx environment

from typing import List, Tuple
import cvxpy as cvx  # type: ignore


def piecewise(
    x: cvx.expressions.expression.Expression,
    y: cvx.expressions.expression.Expression,
    x_intervals: cvx.expressions.constants.parameter.Parameter,
    y_intervals: cvx.expressions.constants.parameter.Parameter,
) -> List[cvx.constraints.constraint.Constraint]:
    """
    Use SOS2 construction to linearize a function, see
    see http://winglpk.sourceforge.net/media/glpk-sos2_02.pdf
    """
    blocks = len(x_intervals.value)
    n = len(x_intervals.value[0])
    z = cvx.Variable((blocks, n - 1), boolean=True)
    s = cvx.Variable((blocks, n - 1))
    x_interval_diff = x_intervals[:, 1:] - x_intervals[:, 0 : n - 1]
    x_ex_last = x_intervals[:, 0 : n - 1]
    y_interval_diff = y_intervals[:, 1:] - y_intervals[:, 0 : n - 1]
    y_ex_last = y_intervals[:, 0 : n - 1]

    return [
        z @ ([1] * (n - 1)) == 1,
        [[0] * blocks] * (n - 1) <= s,
        s <= z,
        x
        == (cvx.multiply(x_ex_last, z) + cvx.multiply(x_interval_diff, s))
        @ ([1] * (n - 1)),
        y
        == (cvx.multiply(y_ex_last, z) + cvx.multiply(y_interval_diff, s))
        @ ([1] * (n - 1)),
    ]


def nf4r(  # type: ignore
    x: cvx.expressions.expression.Expression,
    y: cvx.expressions.expression.Expression,
    z: cvx.expressions.expression.Expression,
    bounds_x: cvx.expressions.constants.parameter.Parameter,
    bounds_y: Tuple[float, float],
) -> List[cvx.constraints.constraint.Constraint]:
    # See Gounaris, 2009
    forecast_block_count = x.shape[0]
    segments = bounds_x.shape[1] - 1

    dy_n = cvx.Variable(
        (forecast_block_count, segments),
    )
    lambda_n = cvx.Variable(
        (forecast_block_count, segments),
        boolean=True,
    )

    segment_ones = cvx.Parameter(segments, value=[1] * segments)
    forecast_ones = cvx.Parameter(
        forecast_block_count,
        value=[1] * forecast_block_count,
    )

    # @ = matrix multiplication, see pep-0465
    return [
        # eq 21
        lambda_n @ segment_ones == forecast_ones,
        # eq 24
        cvx.multiply(
            bounds_x[:, 0:segments],
            lambda_n,
        )
        @ segment_ones
        <= x,
        x <= cvx.multiply(bounds_x[:, 1:], lambda_n) @ segment_ones,
        # 36
        y == bounds_y[0] + dy_n @ segment_ones,
        0 <= dy_n,
        dy_n <= (bounds_y[1] - bounds_y[0]) * lambda_n,
        # 44
        z
        >= bounds_y[1] * x
        + cvx.multiply(bounds_x[:, 1:], dy_n) @ segment_ones
        - (bounds_y[1] - bounds_y[0])
        * (cvx.multiply(bounds_x[:, 1:], lambda_n) @ segment_ones),
        z
        <= bounds_y[1] * x
        + cvx.multiply(bounds_x[:, 0:segments], dy_n) @ segment_ones
        - (bounds_y[1] - bounds_y[0])
        * (cvx.multiply(bounds_x[:, 0:segments], lambda_n) @ segment_ones),
        z <= bounds_y[0] * x + cvx.multiply(bounds_x[:, 1:], dy_n) @ segment_ones,
        # 45
        z
        >= bounds_y[0] * x + cvx.multiply(bounds_x[:, 0:segments], dy_n) @ segment_ones,
    ]
