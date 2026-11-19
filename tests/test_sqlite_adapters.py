"""Run the existing mocked sampling/training/recovery contracts on SQLite."""

import test_paid_adapter as sampling_contract
import test_recovery as recovery_contract
import test_rl_pilot as training_contract


class SQLiteSamplingTests(sampling_contract.TransportTests):
    def setUp(self):
        super().setUp()
        self.ledger.migrate()


class SQLiteTrainingTests(training_contract.DurableRLTests):
    def setUp(self):
        super().setUp()
        self.transport.ledger.migrate()


class SQLiteRecoveryTests(recovery_contract.RecoveryTests):
    def setUp(self):
        super().setUp()
        self.ledger.migrate()
