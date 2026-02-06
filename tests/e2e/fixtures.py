from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

TEST_REPORT_ID = "123"
TEST_REPORT_KEY = "abc"
TEST_REPORT_URL = f"https://myuneekor.com/report?id={TEST_REPORT_ID}&key={TEST_REPORT_KEY}"


@dataclass
class FakeResponse:
    payload: Any
    status_code: int = 200

    def json(self) -> Any:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def build_mock_sessions() -> List[Dict[str, Any]]:
    return [
        {
            "name": "Driver",
            "id": "session-1",
            "shots": [
                {
                    "id": 1,
                    "ball_speed": 50,
                    "club_speed": 40,
                    "carry_distance": 200,
                    "total_distance": 210,
                    "launch_angle": 12.5,
                    "side_spin": 150,
                    "back_spin": 2200,
                },
                {
                    "id": 2,
                    "ball_speed": 52,
                    "club_speed": 41,
                    "carry_distance": 205,
                    "total_distance": 215,
                    "launch_angle": 13.1,
                    "side_spin": 175,
                    "back_spin": 2100,
                },
            ],
        },
        {
            "name": "7 Iron",
            "id": "session-2",
            "shots": [
                {
                    "id": 1,
                    "ball_speed": 35,
                    "club_speed": 30,
                    "carry_distance": 150,
                    "total_distance": 155,
                    "launch_angle": 18.3,
                    "side_spin": 90,
                    "back_spin": 5400,
                }
            ],
        },
    ]


def build_shot_payload(
    shot_id: str,
    session_id: str,
    club: str,
    carry: float,
    total: float,
    ball_speed: float,
    club_speed: float,
    smash: float | None = None,
    launch_angle: float | None = None,
) -> Dict[str, Any]:
    return {
        "id": shot_id,
        "session": session_id,
        "club": club,
        "carry": carry,
        "total": total,
        "ball_speed": ball_speed,
        "club_speed": club_speed,
        "smash": smash,
        "launch_angle": launch_angle,
    }
