import math
import unittest

from juego_lleva.desktop3d_logic import mundo_desde_logico, entrada_relativa


class Desktop3DLogicTests(unittest.TestCase):
    def test_logical_center_maps_to_world_origin(self):
        self.assertEqual(mundo_desde_logico(640, 360), (0.0, 0.0))

    def test_logical_corners_map_to_world_bounds(self):
        self.assertEqual(mundo_desde_logico(0, 0), (-6.4, -3.6))
        self.assertEqual(mundo_desde_logico(1280, 720), (6.4, 3.6))

    def test_forward_at_zero_yaw_maps_to_down_axis(self):
        result = entrada_relativa({"w": True}, 0.0)
        self.assertTrue(result["abajo"])
        self.assertFalse(result["arriba"])
        self.assertFalse(result["izquierda"])
        self.assertFalse(result["derecha"])

    def test_camera_rotation_changes_forward_axis(self):
        result = entrada_relativa({"w": True}, math.pi / 2)
        self.assertTrue(result["derecha"])
        self.assertFalse(result["izquierda"])

    def test_diagonal_input_activates_two_axes(self):
        result = entrada_relativa({"w": True, "d": True}, 0.0)
        self.assertTrue(result["abajo"])
        self.assertTrue(result["derecha"])


if __name__ == "__main__":
    unittest.main()
