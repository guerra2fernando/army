"""
Intent contract helpers for schema validation, clarification flows, and
approval detection.

These utilities provide lightweight validation without requiring external
services. JSON Schema validation is attempted if the `jsonschema` package is
available; otherwise a simplified validator is used.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.db import Database

try:  # Optional dependency
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover - optional import
    jsonschema = None


# --------------------------------------------------------------------------- #
# Clarification flow
# --------------------------------------------------------------------------- #


@dataclass
class ClarificationQuestion:
    """Represents a question to ask the user to fix a payload gap."""

    question: str
    options: Optional[List[str]] = None
    required: bool = False


class ClarificationFlow:
    """
    Multi-question clarification helper.

    This class does not perform user interaction; instead it determines which
    questions should be asked next so the caller can surface them to the user.
    """

    def __init__(self, contract: dict, payload: dict, max_questions: int = 3):
        self.contract = contract or {}
        self.payload = payload or {}
        self.max_questions = max_questions
        self.questions_asked: List[ClarificationQuestion] = []

    def next_questions(self) -> List[ClarificationQuestion]:
        """Return up to `max_questions` clarification questions."""
        pending: List[ClarificationQuestion] = []
        for rule in self.contract.get("clarification_rules", []):
            if self._needs_clarification(rule):
                pending.append(
                    ClarificationQuestion(
                        question=rule.get("question", "Please clarify."),
                        options=rule.get("options"),
                        required=bool(rule.get("required", False)),
                    )
                )

        # Prioritise required questions and cap to max_questions
        pending.sort(key=lambda q: (not q.required, q.question))
        return pending[: self.max_questions]

    def _needs_clarification(self, rule: dict) -> bool:
        """Evaluate a clarification rule against the current payload."""
        condition = rule.get("condition", "")
        return IntentContractService.check_condition(condition, self.payload)


# --------------------------------------------------------------------------- #
# Core service
# --------------------------------------------------------------------------- #


class IntentContractService:
    """
    Contract validation + approval helper.

    Contracts live in the `intent_contracts` collection with shape:
    {
        "agent_name": "JOB_HUNTER",
        "version": "1.0.0",
        "payload_schema": {...},
        "clarification_rules": [...],
        "approval_required": {...}
    }
    """

    def __init__(self, collection=None):
        self.collection = collection or Database.get_collection("intent_contracts")

    async def get_contract(self, agent_name: str) -> Optional[dict]:
        """Return the latest contract for an agent."""
        if not self.collection:
            return None
        return await self.collection.find_one(
            {"agent_name": agent_name},
            sort=[("version", -1)],
        )

    async def validate(self, agent_name: str, payload: dict) -> Dict[str, Any]:
        """
        Validate a payload against the agent's contract.

        Returns:
            {
                "valid": bool,
                "errors": List[str],
                "clarifications": List[ClarificationQuestion],
                "needs_approval": bool,
                "approval_reason": Optional[str],
                "approval_context": dict,
                "actions": {"reversible": [...], "irreversible": [...]}
            }
        """
        contract = await self.get_contract(agent_name)
        if not contract:
            return {"valid": True, "contract": None}

        errors = self._validate_schema(contract.get("payload_schema"), payload)
        clarifications: List[ClarificationQuestion] = []

        if contract.get("clarification_rules"):
            flow = ClarificationFlow(contract, payload)
            clarifications = flow.next_questions()

        needs_approval, approval_reason = self._requires_approval(
            contract.get("approval_required", {}) or {},
            payload,
        )

        reversible, irreversible = self._split_actions(payload)

        return {
            "valid": not errors and not clarifications,
            "errors": errors,
            "clarifications": clarifications,
            "needs_approval": needs_approval,
            "approval_reason": approval_reason,
            "approval_context": contract.get("approval_context", {}),
            "contract": contract,
            "actions": {"reversible": reversible, "irreversible": irreversible},
        }

    # ------------------------------------------------------------------ #
    # Schema validation
    # ------------------------------------------------------------------ #
    def _validate_schema(self, schema: Optional[dict], payload: dict) -> List[str]:
        """Validate payload using jsonschema when available or a lite fallback."""
        if not schema:
            return []

        # Prefer jsonschema when present
        if jsonschema:
            try:
                jsonschema.validate(payload, schema)  # type: ignore[arg-type]
                return []
            except Exception as exc:  # pragma: no cover - exercised in fallback
                return [str(exc)]

        # Fallback: minimal checks for required fields, enum, and type/length constraints
        errors: List[str] = []
        required = schema.get("required") or []
        for field in required:
            if field not in payload or payload.get(field) in (None, "", [], {}):
                errors.append(f"{field} is required")

        properties: Dict[str, dict] = schema.get("properties") or {}
        for field, rules in properties.items():
            if field not in payload:
                continue
            value = payload.get(field)
            expected_type = rules.get("type")
            if expected_type and not self._is_type(value, expected_type):
                errors.append(f"{field} must be of type {expected_type}")

            if "enum" in rules and value not in rules["enum"]:
                errors.append(f"{field} must be one of {rules['enum']}")

            if isinstance(value, (list, tuple)) and rules.get("minItems") is not None:
                if len(value) < int(rules["minItems"]):
                    errors.append(f"{field} must contain at least {rules['minItems']} items")

            if isinstance(value, (int, float)):
                if rules.get("minimum") is not None and value < rules["minimum"]:
                    errors.append(f"{field} must be >= {rules['minimum']}")
                if rules.get("maximum") is not None and value > rules["maximum"]:
                    errors.append(f"{field} must be <= {rules['maximum']}")

        return errors

    @staticmethod
    def _is_type(value: Any, expected: str) -> bool:
        """Very small helper to map JSON schema types to Python types."""
        mapping = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "array": list,
            "object": dict,
            "boolean": bool,
        }
        py_type = mapping.get(expected)
        if not py_type:
            return True
        return isinstance(value, py_type)

    # ------------------------------------------------------------------ #
    # Clarification helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def check_condition(condition: str, payload: dict) -> bool:
        """Evaluate a named condition against payload."""
        condition = (condition or "").lower()
        if condition == "search_terms_empty":
            terms = payload.get("search_terms") or payload.get("roles") or []
            return not terms

        if condition == "location_ambiguous":
            location = (payload.get("location") or "").lower()
            allowed = {"remote", "london", "new_york", "san_francisco", "nyc", "sf"}
            return not location or location not in allowed

        if condition.startswith("missing:"):
            field = condition.split(":", 1)[1]
            return field not in payload or payload.get(field) in (None, "", [], {})

        if condition.startswith("enum:"):
            _, field, values = condition.split(":", 2)
            allowed = {v.strip().lower() for v in values.split(",") if v.strip()}
            val = str(payload.get(field, "")).lower()
            return val not in allowed

        return False

    # ------------------------------------------------------------------ #
    # Approval helpers
    # ------------------------------------------------------------------ #
    def _requires_approval(self, approval_cfg: dict, payload: dict) -> Tuple[bool, Optional[str]]:
        """Determine if the payload is high-risk and needs approval."""
        if not approval_cfg:
            return False, None

        action = (payload.get("action") or payload.get("operation") or "").lower()
        reason: Optional[str] = None

        if approval_cfg.get("high_risk_actions") and action in {
            "apply",
            "apply_job",
            "execute_trade",
            "send_offer",
            "deploy",
        }:
            reason = "High-risk action detected"

        budget_limit = approval_cfg.get("budget_exceeds")
        if budget_limit is not None:
            estimate = payload.get("estimated_hours") or payload.get("budget") or payload.get("max_applications")
            if isinstance(estimate, (int, float)) and estimate > budget_limit:
                reason = f"Budget/limit exceeds {budget_limit}"

        if approval_cfg.get("new_technologies") and payload.get("technology_stack_new"):
            reason = "Uses unapproved technologies"

        if approval_cfg.get("new_company_types") and payload.get("company_type") not in (
            None,
            "approved",
        ):
            reason = "New company type requested"

        return (reason is not None), reason

    # ------------------------------------------------------------------ #
    # Action helpers
    # ------------------------------------------------------------------ #
    def _split_actions(self, payload: dict) -> Tuple[List[dict], List[dict]]:
        """Split payload actions into reversible/irreversible lists."""
        actions = payload.get("actions")
        if not isinstance(actions, list):
            return [], []

        reversible: List[dict] = []
        irreversible: List[dict] = []

        for action in actions:
            if not isinstance(action, dict):
                continue
            if action.get("reversible", False):
                reversible.append(action)
            else:
                irreversible.append(action)

        return reversible, irreversible

    # ------------------------------------------------------------------ #
    # Test utilities
    # ------------------------------------------------------------------ #
    async def seed_contract(
        self,
        *,
        agent_name: str,
        payload_schema: Optional[dict] = None,
        clarification_rules: Optional[List[dict]] = None,
        approval_required: Optional[dict] = None,
        version: str = "1.0.0",
    ) -> dict:
        """Create or upsert a contract (useful in tests)."""
        doc = {
            "contract_id": str(uuid4()),
            "agent_name": agent_name,
            "version": version,
            "payload_schema": payload_schema or {},
            "clarification_rules": clarification_rules or [],
            "approval_required": approval_required or {},
        }
        await self.collection.update_one(
            {"agent_name": agent_name, "version": version},
            {"$set": doc},
            upsert=True,
        )
        return doc










