"""
Tests for LocalPoller idle-cycle visibility.
"""
from unittest.mock import MagicMock


class TestLocalPollerIdleLogging:
    """Tests for idle logging behavior in the main poll loop."""

    def test_record_idle_cycle_logs_info_on_first_cycle(self):
        """The first idle cycle should emit an INFO log for visibility."""
        from poller.main import LocalPoller

        poller = LocalPoller.__new__(LocalPoller)
        poller.logger = MagicMock()
        poller._idle_cycles = 0

        poller._record_idle_cycle()

        assert poller._idle_cycles == 1
        poller.logger.debug.assert_called_once_with("No tasks available")
        poller.logger.info.assert_called_once()
        assert "idle cycles: 1" in poller.logger.info.call_args[0][0]

    def test_record_idle_cycle_logs_info_every_fifth_cycle(self):
        """Later idle cycles should emit INFO periodically, not every loop."""
        from poller.main import LocalPoller

        poller = LocalPoller.__new__(LocalPoller)
        poller.logger = MagicMock()
        poller._idle_cycles = 4

        poller._record_idle_cycle()

        assert poller._idle_cycles == 5
        poller.logger.info.assert_called_once()
        assert "idle cycles: 5" in poller.logger.info.call_args[0][0]

    def test_reset_idle_cycles_logs_when_work_arrives(self):
        """New work should reset the idle counter and explain the transition."""
        from poller.main import LocalPoller

        poller = LocalPoller.__new__(LocalPoller)
        poller.logger = MagicMock()
        poller._idle_cycles = 3

        poller._reset_idle_cycles("task", "task-123")

        assert poller._idle_cycles == 0
        poller.logger.info.assert_called_once_with(
            "Received task task-123 after 3 idle cycle(s)"
        )
