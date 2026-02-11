"""Custom exceptions for the workflow engine."""


class SpecError(Exception):
    """A spec check failed and the step cannot proceed."""

    def __init__(self, rule_id: str, message: str, suggested_fix: str = ""):
        self.rule_id = rule_id
        self.message = message
        self.suggested_fix = suggested_fix
        super().__init__(f"Spec '{rule_id}' failed: {message}")


class BudgetExhaustedError(Exception):
    """A budget limit was reached (retries, total steps, etc.)."""

    def __init__(self, budget_name: str, limit: int):
        self.budget_name = budget_name
        self.limit = limit
        super().__init__(f"Budget '{budget_name}' exhausted (limit: {limit})")


class LoopDetectedError(Exception):
    """Same step executing with identical context fingerprint."""

    def __init__(self, step_id: str, fingerprint: str):
        self.step_id = step_id
        self.fingerprint = fingerprint
        super().__init__(
            f"Loop detected: step '{step_id}' repeated with fingerprint {fingerprint}"
        )


class ManifestError(Exception):
    """Invalid or missing manifest definition."""


class AgentError(Exception):
    """An agent failed during execution."""

    def __init__(self, agent_id: str, message: str):
        self.agent_id = agent_id
        super().__init__(f"Agent '{agent_id}' failed: {message}")
