import math
import numpy as np


def points_sort_clockwise(points):
    points = np.array(points)
    origin = np.mean(points, axis=0)
    refvec = [0, 1]

    def clockwiseangle_and_distance(point):
        # Vector between point and the origin: v = p - o
        vector = [point[0] - origin[0], point[1] - origin[1]]
        # Length of vector: ||v||
        lenvector = math.hypot(vector[0], vector[1])
        # If length is zero there is no angle
        if lenvector == 0:
            return -math.pi, 0
        # Normalize vector: v/||v||
        normalized = [vector[0] / lenvector, vector[1] / lenvector]
        dotprod = normalized[0] * refvec[0] + normalized[1] * refvec[1]  # x1*x2 + y1*y2
        diffprod = (
            refvec[1] * normalized[0] - refvec[0] * normalized[1]
        )  # x1*y2 - y1*x2
        angle = math.atan2(diffprod, dotprod)
        # Negative angles represent counter-clockwise angles so we need to subtract them
        # from 2*pi (360 degrees)
        if angle < 0:
            return 2 * math.pi + angle, lenvector
        # I return first the angle because that's the primary sorting criterium
        # but if two vectors have the same angle then the shorter distance should come first.
        return angle, lenvector

    return np.array(sorted(points, key=clockwiseangle_and_distance))


# polygon has to be clockwise
def check_point_in_polygon(point, polygon):
    for i in range(len(polygon)):
        if (point[0] - polygon[i - 1, 0]) * (polygon[i, 1] - polygon[i - 1, 1]) - (
            point[1] - polygon[i - 1, 1]
        ) * (polygon[i, 0] - polygon[i - 1, 0]) < 0:
            return False

    return True


def line_intersection(line1, line2):
    [x1, y1], [x2, y2] = line1
    [x3, y3], [x4, y4] = line2
    xdiff = (x1 - x2, x3 - x4)
    ydiff = (y1 - y2, y3 - y4)

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        return None

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return [x, y]


def line_polygon_intersection(line, polygon):
    intersections = []
    for i in range(len(polygon)):
        line2 = [polygon[i - 1], polygon[i]]
        sec = line_intersection(line, line2)
        if sec is not None:
            if (sec[0] - line2[0][0]) * (sec[0] - line2[1][0]) <= 0:
                intersections.append(sec)

    if len(intersections) == 2:
        return intersections
    else:
        return None


def test_polygon():
    points = [[0, 10], [10, 5], [0, 50], [70, 35]]
    points = points_sort_clockwise(points)
    pt = [10, 10]
    pt2 = [10, 4]
    assert check_point_in_polygon(pt, np.array(points)) & (
        not check_point_in_polygon(pt2, np.array(points))
    )


def test_intersection():
    polygon = [[0, 10], [10, 5], [0, 50], [70, 35]]
    polygon = points_sort_clockwise(polygon)
    line1 = [[20, 0], [20, 10]]
    sec1 = line_polygon_intersection(line1, polygon)
    y_sec1 = [sec1[0][1], sec1[1][1]]
    assert (sec1[0][0] == 20) & (min(y_sec1) == 10) & (abs(max(y_sec1) - 45.7) < 0.1)

    line2 = [[0, 0], [0, 10]]
    sec2 = line_polygon_intersection(line2, polygon)
    y_sec2 = [sec2[0][1], sec2[1][1]]
    assert (sec2[0][0] == 0) & (min(y_sec2) == 10) & (max(y_sec2) == 50)

    line3 = [[80, 0], [80, 10]]
    sec3 = line_polygon_intersection(line3, polygon)
    assert sec3 is None


if __name__ == "__main__":
    test_polygon()
    test_intersection()
