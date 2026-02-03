import os
import sys
import tempfile
import types
import unittest
import importlib

try:
    import golf_db
    from tests.e2e.fixtures import build_shot_payload
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "Required dependencies not installed")
class TestCoachFlow(unittest.TestCase):
    @staticmethod
    def _install_ml_stubs():
        if "ml.train_models" in sys.modules:
            return

        sys.modules.setdefault("ml", types.ModuleType("ml"))

        train_models = types.ModuleType("ml.train_models")

        class DistancePredictor:
            model_path = ""

            def load(self):
                return None

        train_models.DistancePredictor = DistancePredictor
        sys.modules["ml.train_models"] = train_models

        classifiers = types.ModuleType("ml.classifiers")

        class ShotShapeClassifier:
            pass

        def classify_shot_shape(*_args, **_kwargs):
            return None

        class ShotShape:
            pass

        classifiers.ShotShapeClassifier = ShotShapeClassifier
        classifiers.classify_shot_shape = classify_shot_shape
        classifiers.ShotShape = ShotShape
        sys.modules["ml.classifiers"] = classifiers

        anomaly_detection = types.ModuleType("ml.anomaly_detection")

        class SwingFlawDetector:
            pass

        def detect_swing_flaws(*_args, **_kwargs):
            return []

        class SwingFlaw:
            pass

        anomaly_detection.SwingFlawDetector = SwingFlawDetector
        anomaly_detection.detect_swing_flaws = detect_swing_flaws
        anomaly_detection.SwingFlaw = SwingFlaw
        sys.modules["ml.anomaly_detection"] = anomaly_detection

    @classmethod
    def setUpClass(cls):
        cls._install_ml_stubs()
        try:
            cls.local_coach = importlib.import_module("local_coach")
        except Exception as exc:
            raise unittest.SkipTest(f"local_coach import failed: {exc}") from exc

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "golf_stats.db")

        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.set_read_mode("sqlite")
        golf_db.init_db()

        shots = [
            build_shot_payload(
                shot_id="c1-1",
                session_id="coach-1",
                club="Driver",
                carry=255,
                total=270,
                ball_speed=167,
                club_speed=112,
                smash=1.49,
                launch_angle=13.0,
            ),
            build_shot_payload(
                shot_id="c1-2",
                session_id="coach-1",
                club="Driver",
                carry=250,
                total=265,
                ball_speed=164,
                club_speed=110,
                smash=1.49,
                launch_angle=12.0,
            ),
            build_shot_payload(
                shot_id="c2-1",
                session_id="coach-2",
                club="7 Iron",
                carry=160,
                total=165,
                ball_speed=118,
                club_speed=85,
                smash=1.39,
                launch_angle=18.5,
            ),
        ]

        for shot in shots:
            golf_db.save_shot(shot)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_coach_driver_query(self):
        coach = self.local_coach.LocalCoach()
        response = coach.get_response("How's my driver doing?")

        self.assertIn("Driver", response.message)
        self.assertIsNotNone(response.data)
        self.assertIn("carry", response.data)

    def test_coach_comparison_query(self):
        coach = self.local_coach.LocalCoach()
        response = coach.get_response("compare my clubs")

        self.assertIn("Club Comparison", response.message)
        self.assertIsNotNone(response.data)
        self.assertIn("clubs", response.data)


if __name__ == "__main__":
    unittest.main()
