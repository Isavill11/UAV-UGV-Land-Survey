import unittest
import tempfile
import yaml
import os

from verify_config import SelfCheckPrelaunch, PrecheckError


class TestCasesConfig(unittest.TestCase):
    
    def test_missing_config_file(self):
        check = SelfCheckPrelaunch("C:/Users/16614/VSCode Projects/rasp_for_uavugv/UAV-UGV-Land-Survey/Raspberry_Pi_Agent/nonexistent.yaml")
        error = check._check_config()

        self.assertIsNotNone(error)
        self.assertEqual(error.subsystem, "Config")
        self.assertIn("not found", error.message.lower())

    def test_empty_yaml_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            path = f.name

        check = SelfCheckPrelaunch(path)
        error = check._check_config()

        self.assertIsNotNone(error)

        os.remove(path)
        
    def test_not_dict_config_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            yaml.dump(["this", "is", "a", "list"], f)
            path = f.name

        check = SelfCheckPrelaunch(path)
        error = check._check_config()

        self.assertIsNotNone(error)
        self.assertEqual(error.subsystem, "Config")
        self.assertIn("dictionary", error.message.lower())

        os.remove(path)

    def test_invalid_yaml_syntax(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("platform: [unclosed list")
            path = f.name

        check = SelfCheckPrelaunch(path)
        error = check._check_config()

        self.assertIsNotNone(error)
        self.assertIn("yaml", error.message.lower())

        os.remove(path)

    def test_missing_required_keys(self):
        bad_config = {
            "platform": {
                "name": "UAV",
                "id": "001"
                # missing location
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            yaml.dump(bad_config, f)
            path = f.name

        check = SelfCheckPrelaunch(path)
        check._check_config()  # load config
        error = check._check_required_keys()

        self.assertIsNotNone(error)
        self.assertIn("missing required key", error.message.lower())

        os.remove(path)

    def test_wrong_type_in_config(self):
        bad_config = {
            "platform": {
                "name": "UAV",
                "id": 123,  # should be str
                "location": "Texas"
            },
            "camera": {
                "id": "cam1",
                "type": "RGB",
                "dimensions": {"width": "640", "height": 480},  # width wrong type
                "capture_profiles": {
                    "CAPTURING": {},
                    "DEGRADED": {},
                    "CRITICAL": {}
                }
            },
            "storage": {"local_path": "/tmp"},
            "battery_status": {"critical_battery": 10, "low_battery": 20}
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            yaml.dump(bad_config, f)
            path = f.name

        check = SelfCheckPrelaunch(path)
        check._check_config()
        error = check._check_required_keys()

        self.assertIsNotNone(error)
        self.assertIn("must be of type", error.message.lower())

        os.remove(path)
        
    def test_wrong_camera(self): 
        pass
    
    def test_no_storage(self):
        pass
    def test_network_error(self):
        pass

if __name__ == "__main__":
    unittest.main(verbosity=2)
