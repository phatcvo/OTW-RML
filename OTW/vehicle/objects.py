from abc import ABC
from typing import Sequence, Tuple, TYPE_CHECKING, Optional
import numpy as np

from OTW.common import utils

if TYPE_CHECKING:
    from OTW.road.road import AbstractLane
    from OTW.road.road import Road

LaneIndex = Tuple[str, str, int]

# Common interface for objects that appear on the road. For now we assume all objects are rectangular.
class RoadObject(ABC):
    LENGTH: float = 2  # Object length [m]
    WIDTH: float = 2  # Object width [m]

    def __init__(self, road: 'Road', position: Sequence[float], heading: float = 0, speed: float = 0):
        self.road = road # the road instance where the object is placed in
        self.position = np.array(position, dtype=np.float) # cartesian position of object in the surface
        self.heading = heading # the angle from positive direction of horizontal axis
        self.speed = speed # cartesian speed of object in the surface
        self.lane_index = self.road.network.get_closest_lane_index(self.position, self.heading) if self.road else np.nan
        self.lane = self.road.network.get_lane(self.lane_index) if self.road else None

        # Enable collision with other collidables
        self.collidable = True

        # Collisions have physical effects
        self.solid = True

        # If False, this object will not check its own collisions, but it can still collides with other objects that do
        # check their collisions.
        self.check_collisions = True

        self.crashed = False
        self.hit = False
        self.impact = np.zeros(self.position.shape)

    # Create a vehicle on a given lane at a longitudinal position.
    """
    :param road: a road object containing the road network
    :param lane_index: index of the lane where the object is located
    :param longitudinal: longitudinal position along the lane
    :param speed: initial speed in [m/s]
    """
    @classmethod
    def make_on_lane(cls, road: 'Road', lane_index: LaneIndex, longitudinal: float, speed: Optional[float] = None) \
            -> 'RoadObject':

        lane = road.network.get_lane(lane_index)
        if speed is None:
            speed = lane.speed_limit
        # a RoadObject at the specified position
        return cls(road, lane.position(longitudinal, 0), lane.heading_at(longitudinal), speed)

    # Check for collision with another vehicle.
    def handle_collisions(self, other: 'RoadObject', dt: float = 0) -> None:
        if other is self or not (self.check_collisions or other.check_collisions):
            return
        if not (self.collidable and other.collidable):
            return
        intersecting, will_intersect, transition = self._is_colliding(other, dt)
        if will_intersect:
            if self.solid and other.solid:
                self.impact = transition / 2
                other.impact = -transition / 2
        if intersecting:
            if self.solid and other.solid:
                self.crashed = True
                other.crashed = True
            if not self.solid:
                self.hit = True
            if not other.solid:
                other.hit = True

    def _is_colliding(self, other, dt):
        # Fast spherical pre-check
        if np.linalg.norm(other.position - self.position) > self.LENGTH + self.speed * dt:
            return False, False, np.zeros(2,)
        # Accurate rectangular check
        return utils.are_polygons_intersecting(self.polygon(), other.polygon(), self.velocity * dt, other.velocity * dt)

    # Just added for sake of compatibility
    def to_dict(self, origin_vehicle=None, observe_intentions=True):
        d = {
            'presence': 1,
            'x': self.position[0],
            'y': self.position[1],
            'vx': 0.,
            'vy': 0.,
            'cos_h': np.cos(self.heading),
            'sin_h': np.sin(self.heading),
            'cos_d': 0.,
            'sin_d': 0.
        }
        if not observe_intentions:
            d["cos_d"] = d["sin_d"] = 0
        if origin_vehicle:
            origin_dict = origin_vehicle.to_dict()
            for key in ['x', 'y', 'vx', 'vy']:
                d[key] -= origin_dict[key]
        return d

    @property
    def direction(self) -> np.ndarray:
        return np.array([np.cos(self.heading), np.sin(self.heading)])

    @property
    def velocity(self) -> np.ndarray:
        return self.speed * self.direction

    def polygon(self) -> np.ndarray:
        points = np.array([
            [-self.LENGTH / 2, -self.WIDTH / 2],
            [-self.LENGTH / 2, +self.WIDTH / 2],
            [+self.LENGTH / 2, +self.WIDTH / 2],
            [+self.LENGTH / 2, -self.WIDTH / 2],
        ]).T
        c, s = np.cos(self.heading), np.sin(self.heading)
        rotation = np.array([
            [c, -s],
            [s, c]
        ])
        points = (rotation @ points).T + np.tile(self.position, (4, 1))
        return np.vstack([points, points[0:1]])

    # Compute the signed distance to another object along a lane.
    def lane_distance_to(self, other: 'RoadObject', lane: 'AbstractLane' = None) -> float:
        # other is the other object
        if not other:
            return np.nan
        if not lane:
            lane = self.lane
        # the distance to the other other [m]
        return lane.local_coordinates(other.position)[0] - lane.local_coordinates(self.position)[0]

    # Is the object on its current lane, or off-road?
    @property
    def on_road(self) -> bool:
        return self.lane.on_lane(self.position)

    def front_distance_to(self, other: "RoadObject") -> float:
        return self.direction.dot(other.position - self.position)

    def __str__(self):
        return f"{self.__class__.__name__} #{id(self) % 1000}: at {self.position}"

    def __repr__(self):
        return self.__str__()

# Obstacles on the road.
class Obstacle(RoadObject):
    def __init__(self, road, position: Sequence[float], heading: float = 0, speed: float = 0):
        super().__init__(road, position, heading, speed)
        self.solid = True

# Landmarks of certain areas on the road that must be reached.
class Landmark(RoadObject):
    def __init__(self, road, position: Sequence[float], heading: float = 0, speed: float = 0):
        super().__init__(road, position, heading, speed)
        self.solid = False

