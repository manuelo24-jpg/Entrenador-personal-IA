from __future__ import annotations

import math

from app.core.pose.base import Person


class PersonTracker:
    """
    Selects and maintains focus on the primary athlete in multi-person frames
    based on bounding box size, frame centrality, and persistent track_id.
    """

    def __init__(self) -> None:
        self.active_track_id: int | None = None
        self.last_center: tuple[float, float] | None = None

    def reset(self) -> None:
        self.active_track_id = None
        self.last_center = None

    def select(
        self,
        persons: list[Person],
        frame_width: int,
        frame_height: int,
    ) -> Person | None:
        if not persons:
            return None

        if len(persons) == 1:
            chosen = persons[0]
            self.active_track_id = chosen.track_id
            self.last_center = chosen.center
            return chosen

        # If active_track_id is present in current detections, prefer it
        if self.active_track_id is not None:
            for p in persons:
                if p.track_id == self.active_track_id:
                    self.last_center = p.center
                    return p

        frame_area = max(1.0, float(frame_width * frame_height))
        frame_cx = frame_width * 0.5
        frame_cy = frame_height * 0.5
        frame_diag = max(1.0, math.hypot(frame_width, frame_height))

        best_person: Person | None = None
        best_score = -1e9

        for p in persons:
            area_ratio = p.area / frame_area
            px, py = p.center
            center_dist = math.hypot(px - frame_cx, py - frame_cy) / frame_diag
            continuity_bonus = 0.0
            if self.last_center is not None:
                prev_dist = (
                    math.hypot(px - self.last_center[0], py - self.last_center[1]) / frame_diag
                )
                continuity_bonus = max(0.0, 0.4 - prev_dist)

            score = (area_ratio * 2.0) - (center_dist * 0.8) + continuity_bonus
            if score > best_score:
                best_score = score
                best_person = p

        if best_person is not None:
            self.active_track_id = best_person.track_id
            self.last_center = best_person.center
        return best_person
