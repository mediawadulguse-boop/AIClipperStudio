import unittest
from ai_clipper.config import AppConfig

class ConfigTests(unittest.TestCase):
    def test_default_qwen_model_exists(self):
        cfg = AppConfig()
        self.assertTrue(cfg.qwen_model.startswith("Qwen/"))
        self.assertIn(cfg.ai_mode, ("local_llm", "local_lite"))

if __name__ == "__main__":
    unittest.main()
