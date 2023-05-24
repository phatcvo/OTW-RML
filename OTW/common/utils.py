import copy
import importlib
import itertools
from typing import Tuple, Dict, Callable, List, Optional, Union, Sequence

import numpy as np

# Useful types
Vector = Union[np.ndarray, Sequence[float]]
Matrix = Union[np.ndarray, Sequence[Sequence[float]]]
Interval = Union[np.ndarray, Tuple[Vector, Vector], Tuple[Matrix, Matrix], Tuple[float, float],
                 List[Vector], List[Matrix], List[float]]

def do_every(duration: float, timer: float) -> bool:
    return duration < timer

# Linear map of value v with range x to desired range y.
def lmap(v: float, x: Interval, y: Interval) -> float:
    return y[0] + (v - x[0]) * (y[1] - y[0]) / (x[1] - x[0])

def get_class_path(cls: Callable) -> str:
    return cls.__module__ + "." + cls.__qualname__

def class_from_path(path: str) -> Callable:
    module_name, class_name = path.rsplit(".", 1)
    class_object = getattr(importlib.import_module(module_name), class_name)
    return class_object

def constrain(x: float, a: float, b: float) -> np.ndarray:
    return np.clip(x, a, b)

def not_zero(x: float, eps: float = 1e-2) -> float:
    if abs(x) > eps:
        return x
    elif x >= 0:
        return eps
    else:
        return -eps


def wrap_to_pi(x: float) -> float:
    return ((x + np.pi) % (2 * np.pi)) - np.pi

# Check if a point is inside a rectangle
def point_in_rectangle(point: Vector, rect_min: Vector, rect_max: Vector) -> bool:
    # a point (x, y); rect_min: x_min, y_min; rect_max: x_max, y_max
    return rect_min[0] <= point[0] <= rect_max[0] and rect_min[1] <= point[1] <= rect_max[1]

# Check if a point is inside a rotated rectangle
def point_in_rotated_rectangle(point: np.ndarray, center: np.ndarray, length: float, width: float, angle: float) \
        -> bool:
    c, s = np.cos(angle), np.sin(angle) # [rad]
    r = np.array([[c, -s], [s, c]])
    ru = r.dot(point - center)
    # is the point inside the rectangle
    return point_in_rectangle(ru, (-length/2, -width/2), (length/2, width/2))

# Check if a point is inside an ellipse
def point_in_ellipse(point: Vector, center: Vector, angle: float, length: float, width: float) -> bool:
    c, s = np.cos(angle), np.sin(angle)
    r = np.matrix([[c, -s], [s, c]])
    ru = r.dot(point - center)
    # is the point inside the ellipse
    return np.sum(np.square(ru / np.array([length, width]))) < 1

# Do two rotated rectangles intersect?
def rotated_rectangles_intersect(rect1: Tuple[Vector, float, float, float],
                                 rect2: Tuple[Vector, float, float, float]) -> bool:
    # rect1: (center, length, width, angle)
    # rect2: (center, length, width, angle)
    return has_corner_inside(rect1, rect2) or has_corner_inside(rect2, rect1)

# Check if rect1 has a corner inside rect2
def has_corner_inside(rect1: Tuple[Vector, float, float, float],
                      rect2: Tuple[Vector, float, float, float]) -> bool:
    (c1, l1, w1, a1) = rect1
    (c2, l2, w2, a2) = rect2
    c1 = np.array(c1)
    l1v = np.array([l1/2, 0])
    w1v = np.array([0, w1/2])
    r1_points = np.array([[0, 0],
                          - l1v, l1v, -w1v, w1v,
                          - l1v - w1v, - l1v + w1v, + l1v - w1v, + l1v + w1v])
    c, s = np.cos(a1), np.sin(a1)
    r = np.array([[c, -s], [s, c]])
    rotated_r1_points = r.dot(r1_points.transpose()).transpose()
    return any([point_in_rotated_rectangle(c1+np.squeeze(p), c2, l2, w2, a2) for p in rotated_r1_points])


def project_polygon(polygon: Vector, axis: Vector) -> Tuple[float, float]:
    min_p, max_p = None, None
    for p in polygon:
        projected = p.dot(axis)
        if min_p is None or projected < min_p:
            min_p = projected
        if max_p is None or projected > max_p:
            max_p = projected
    return min_p, max_p

# Calculate the distance between [minA, maxA] and [minB, maxB]; The distance will be negative if the intervals overlap
def interval_distance(min_a: float, max_a: float, min_b: float, max_b: float):
    return min_b - max_a if min_a < min_b else min_a - max_b

# Checks if the two polygons are intersecting.
# See https://www.codeproject.com/Articles/15573/2D-Polygon-Collision-Detection
def are_polygons_intersecting(a: Vector, b: Vector,
                              displacement_a: Vector, displacement_b: Vector) \
        -> Tuple[bool, bool, Optional[np.ndarray]]:

    intersecting = will_intersect = True
    min_distance = np.inf
    translation, translation_axis = None, None
    for polygon in [a, b]:
        for p1, p2 in zip(polygon, polygon[1:]):
            normal = np.array([-p2[1] + p1[1], p2[0] - p1[0]])
            normal /= np.linalg.norm(normal)
            min_a, max_a = project_polygon(a, normal)
            min_b, max_b = project_polygon(b, normal)

            if interval_distance(min_a, max_a, min_b, max_b) > 0:
                intersecting = False

            velocity_projection = normal.dot(displacement_a - displacement_b)
            if velocity_projection < 0:
                min_a += velocity_projection
            else:
                max_a += velocity_projection

            distance = interval_distance(min_a, max_a, min_b, max_b)
            if distance > 0:
                will_intersect = False
            if not intersecting and not will_intersect:
                break
            if abs(distance) < min_distance:
                min_distance = abs(distance)
                d = a[:-1].mean(axis=0) - b[:-1].mean(axis=0)  # center difference
                translation_axis = normal if d.dot(normal) > 0 else -normal

    if will_intersect:
        translation = min_distance * translation_axis
    return intersecting, will_intersect, translation # are intersecting, will intersect, translation vector


# Compute a confidence ellipsoid over the parameter theta, where y = theta^T phi
def confidence_ellipsoid(data: Dict[str, np.ndarray], lambda_: float = 1e-5, delta: float = 0.1, sigma: float = 0.1,
                         param_bound: float = 1.0) -> Tuple[np.ndarray, np.ndarray, float]:
    phi = np.array(data["features"])
    y = np.array(data["outputs"])
    g_n_lambda = 1/sigma * np.transpose(phi) @ phi + lambda_ * np.identity(phi.shape[-1])
    theta_n_lambda = np.linalg.inv(g_n_lambda) @ np.transpose(phi) @ y / sigma
    d = theta_n_lambda.shape[0]
    beta_n = np.sqrt(2*np.log(np.sqrt(np.linalg.det(g_n_lambda) / lambda_ ** d) / delta)) + \
        np.sqrt(lambda_*d) * param_bound
    return theta_n_lambda, g_n_lambda, beta_n # estimated theta, Gramian matrix G_N_lambda, radius beta_N

    # data: a dictionary {"features": [phi_0,...,phi_N], "outputs": [y_0,...,y_N]}
    # parameter_box: a box [theta_min, theta_max]  containing the parameter theta

# Compute a confidence polytope over the parameter theta, where y = theta^T phi
def confidence_polytope(data: dict, parameter_box: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    param_bound = np.amax(np.abs(parameter_box))
    theta_n_lambda, g_n_lambda, beta_n = confidence_ellipsoid(data, param_bound=param_bound)

    values, pp = np.linalg.eig(g_n_lambda)
    radius_matrix = np.sqrt(beta_n) * np.linalg.inv(pp) @ np.diag(np.sqrt(1 / values))
    h = np.array(list(itertools.product([-1, 1], repeat=theta_n_lambda.shape[0])))
    d_theta = np.array([radius_matrix @ h_k for h_k in h])

    # Clip the parameter and confidence region within the prior parameter box.
    theta_n_lambda = np.clip(theta_n_lambda, parameter_box[0], parameter_box[1])
    for k, _ in enumerate(d_theta):
        d_theta[k] = np.clip(d_theta[k], parameter_box[0] - theta_n_lambda, parameter_box[1] - theta_n_lambda)
    # estimated theta, polytope vertices, Gramian matrix G_N_lambda, radius beta_N
    return theta_n_lambda, d_theta, g_n_lambda, beta_n
    # :param y: observation
    # :param phi: feature
    # :param theta: estimated parameter
    # :param gramian: Gramian matrix
    # :param beta: ellipsoid radius
    # :param sigma: noise covariance

# Check if a new observation (phi, y) is valid according to a confidence ellipsoid on theta.
def is_valid_observation(y: np.ndarray, phi: np.ndarray, theta: np.ndarray, gramian: np.ndarray,
                         beta: float, sigma: float = 0.1) -> bool:
    y_hat = np.tensordot(theta, phi, axes=[0, 0])
    error = np.linalg.norm(y - y_hat)
    eig_phi, _ = np.linalg.eig(phi.transpose() @ phi)
    eig_g, _ = np.linalg.eig(gramian)
    error_bound = np.sqrt(np.amax(eig_phi) / np.amin(eig_g)) * beta + sigma
    return error < error_bound # validity of the observation

"""
    :param data: a dictionary {"features": [phi_0,...,phi_N], "outputs": [y_0,...,y_N]}
    :param parameter_box: a box [theta_min, theta_max]  containing the parameter theta
"""
#     Check whether a dataset {phi_n, y_n} is consistent
#     The last observation should be in the confidence ellipsoid obtained by the N-1 first observations.
def is_consistent_dataset(data: dict, parameter_box: np.ndarray = None) -> bool:
    train_set = copy.deepcopy(data)
    y, phi = train_set["outputs"].pop(-1), train_set["features"].pop(-1)
    y, phi = np.array(y)[..., np.newaxis], np.array(phi)[..., np.newaxis]
    if train_set["outputs"] and train_set["features"]:
        theta, _, gramian, beta = confidence_polytope(train_set, parameter_box=parameter_box)
        return is_valid_observation(y, phi, theta, gramian, beta)
    else:
        return True # consistency of the dataset

"""
    You can either set the number of bins, or their size.
    The sum of bins always equals the total.
    :param x: number to split
    :param num_bins: number of bins
    :param size_bins: size of bins
    :return: list of bin sizes
"""
# Split a number into several bins with near-even distribution.
def near_split(x, num_bins=None, size_bins=None):

    if num_bins:
        quotient, remainder = divmod(x, num_bins)
        return [quotient + 1] * remainder + [quotient] * (num_bins - remainder)
    elif size_bins:
        return near_split(x, num_bins=int(np.ceil(x / size_bins)))


def distance_to_circle(center, radius, direction):
    scaling = radius * np.ones((2, 1))
    a = np.linalg.norm(direction / scaling) ** 2
    b = -2 * np.dot(np.transpose(center), direction / np.square(scaling))
    c = np.linalg.norm(center / scaling) ** 2 - 1
    root_inf, root_sup = solve_trinom(a, b, c)
    if root_inf and root_inf > 0:
        distance = root_inf
    elif root_sup and root_sup > 0:
        distance = 0
    else:
        distance = np.infty
    return distance


def solve_trinom(a, b, c):
    delta = b ** 2 - 4 * a * c
    if delta >= 0:
        return (-b - np.sqrt(delta)) / (2 * a), (-b + np.sqrt(delta)) / (2 * a)
    else:
        return None, None