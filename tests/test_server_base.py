import inspect
import sys
import unittest
from pathlib import Path


class TestServerBase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.paths = [
            self.repo_root / "kits" / "python" / "src",
            self.repo_root / "models" / "python" / "src",
        ]
        for path in self.paths:
            sys.path.insert(0, str(path))
        self.daemon_dir = self.repo_root / "kits" / "python" / "src" / "arp_standard_server" / "daemon"

    def tearDown(self) -> None:
        for path in self.paths:
            try:
                sys.path.remove(str(path))
            except ValueError:
                pass

    def test_daemon_server_is_abstract(self) -> None:
        if not self.daemon_dir.exists():
            self.skipTest("Generated server package missing; run codegen before tests.")
        from arp_standard_server.daemon import BaseDaemonServer

        self.assertTrue(inspect.isabstract(BaseDaemonServer))


if __name__ == "__main__":
    unittest.main()
