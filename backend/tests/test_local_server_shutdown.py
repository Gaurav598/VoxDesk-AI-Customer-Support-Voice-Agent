import unittest
from unittest.mock import Mock

from voice_agent.local_server import serve_until_stopped


class LocalServerShutdownTests(unittest.TestCase):
    def test_keyboard_interrupt_closes_server(self):
        server = Mock()
        server.serve_forever.side_effect = KeyboardInterrupt

        serve_until_stopped(server, announce=False)

        server.server_close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
