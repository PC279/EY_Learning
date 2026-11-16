"""
E-commerce Returns & Refund Processing: graph-based multi-agent workflow
=======================================================================

Return Request -> Eligibility Agent -> Risk Agent -> Approval Gateway
               -> Customer Response Agent -> Final Output

- Python rules decide approval; the AI agents only explain, assess and write.
- Requests that fail any rule PAUSE for a human manager (approve / reject),
  then the workflow RESUMES with that decision.
- Simulation only: no payments, messages or replacements are sent.

Run:  python returns_workflow.py
"""

import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Never

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agent_framework import (
    Agent,
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    executor,
    handler,
    response_handler,
)
from agent_framework.exceptions import ChatClientException
from agent_framework.openai import OpenAIChatClient


# =====================================================
# 1. CONFIGURATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parent

# override=True: .env wins over any old variable of the same name set in Windows
load_dotenv(BASE_DIR / ".env", override=True)

REQUIRED_ENV = ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_BASE_URL", "AZURE_OPENAI_MODEL")

# Field names expected in every record of returns.json
REQUIRED_FIELDS = (
    "request_id", "order_id", "product", "product_category", "request_type",
    "amount_inr", "days_since_delivery", "item_condition", "return_reason",
    "invoice_available", "photo_evidence_available", "previous_returns_90_days",
)

# Demo return policy (Task 3)
MAX_AMOUNT_INR = 25_000        # rule 1: amount must be BELOW this
MAX_DAYS = 30                  # rule 2: within 30 days of delivery
MAX_PREVIOUS_RETURNS = 3       # rule 5: FEWER than 3 returns in 90 days


@dataclass
class ManagerApprovalRequest:
    """What the workflow sends out when it pauses for the manager."""
    request: dict      # the full request, so context survives the pause
    prompt: str        # one-line summary shown to the manager


def check_config() -> dict:
    """Stop with a clear message if any Azure setting is missing (Task 7)."""
    missing = [name for name in REQUIRED_ENV if not os.getenv(name, "").strip()]
    if missing:
        sys.exit(
            "CONFIGURATION ERROR: missing " + ", ".join(missing) + ".\n"
            "Copy .env.example to .env and fill in every value."
        )
    return {name: os.environ[name].strip() for name in REQUIRED_ENV}


def load_requests() -> list[dict]:
    """Load returns.json and check every record has the fields the rules need (Task 1)."""
    with (BASE_DIR / "returns.json").open(encoding="utf-8") as file:
        requests = json.load(file)

    for index, record in enumerate(requests, start=1):
        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            sys.exit(f"DATA ERROR: record {index} in returns.json is missing: {', '.join(missing)}")
    return requests


# =====================================================
# 2. DETERMINISTIC BUSINESS RULES (Task 3)
# =====================================================

def check_policy(request: dict) -> list[str]:
    """Return the list of broken rules 1-5. An empty list means the request is eligible."""
    issues = []
    condition = str(request["item_condition"]).strip().lower()

    if request["amount_inr"] >= MAX_AMOUNT_INR:
        issues.append(f"Amount INR {request['amount_inr']:,} is not below INR {MAX_AMOUNT_INR:,}")
    if request["days_since_delivery"] > MAX_DAYS:
        issues.append(f"Requested {request['days_since_delivery']} days after delivery (limit {MAX_DAYS})")
    if not request["invoice_available"]:
        issues.append("Customer invoice is not available")
    if condition == "damaged" and not request["photo_evidence_available"]:
        issues.append("Item is damaged but no supporting photographs were provided")
    elif condition not in ("unopened", "damaged"):
        issues.append(f"Item condition is '{condition}' (must be unopened, or damaged with photos)")
    if request["previous_returns_90_days"] >= MAX_PREVIOUS_RETURNS:
        issues.append(f"{request['previous_returns_90_days']} previous returns in 90 days (must be fewer than {MAX_PREVIOUS_RETURNS})")

    return issues


def parse_risk(text: str) -> tuple[str, str]:
    """Read 'HIGH - reason' or 'LOW - reason'. Anything unclear counts as HIGH (fail-safe)."""
    text = text.strip()
    parts = re.split(r"\s*[-:–—]\s*", text, maxsplit=1)
    level = parts[0].strip(" .*").upper()
    summary = parts[1].strip() if len(parts) > 1 else text
    if level not in ("HIGH", "LOW"):
        return "HIGH", f"Unclear risk answer, treated as HIGH: {text}"
    return level, summary


# Phrases that would wrongly claim the refund/replacement is already done (Task 2)
COMPLETION_CLAIM = re.compile(
    r"\b(has|have) been (processed|issued|credited|refunded|shipped|dispatched|completed|initiated)\b"
    r"|\bwe have (processed|issued|credited|refunded|shipped|dispatched|initiated)\b",
    re.IGNORECASE,
)
SAFE_MESSAGES = {
    "approved": ("Dear Customer, your {kind} request for {product} (order {order_id}) has been approved. "
                 "Our team will contact you with the next steps."),
    "rejected": ("Dear Customer, we are sorry, but your {kind} request for {product} (order {order_id}) "
                 "could not be approved after review. Please contact our support team if you have questions."),
}


def safe_customer_message(draft: str, request: dict) -> str:
    """Keep the AI draft only if it matches the decision and claims nothing is completed."""
    rejected = request["final_decision"] == "MANAGER_REJECTED"
    says_approved = re.search(r"(?<!not )\bapproved\b", draft, re.IGNORECASE)

    if COMPLETION_CLAIM.search(draft) or (rejected and says_approved):
        template = SAFE_MESSAGES["rejected" if rejected else "approved"]
        return template.format(kind=str(request["request_type"]).lower(), product=request["product"],
                               order_id=request["order_id"])
    return draft


# =====================================================
# 3. HUMAN-IN-THE-LOOP APPROVAL GATEWAY (Tasks 3 and 5)
# =====================================================

class ApprovalGateway(Executor):

    def __init__(self):
        super().__init__(id="approval_gateway")

    @handler
    async def review(self, request: dict, ctx: WorkflowContext[dict]) -> None:
        # Rule 6 joins rules 1-5: a HIGH risk also needs a human
        reasons = list(request["eligibility_issues"])
        if request["risk_level"] == "HIGH":
            reasons.append("Risk Agent identified a HIGH risk")

        if not reasons:
            print("  ApprovalGateway: all 6 conditions met -> automatic approval")
            await ctx.send_message({**request, "approval_route": "Automatic",
                                    "final_decision": "AUTO_APPROVED"})
            return

        # PAUSE: the workflow stops here until the manager answers
        print("  ApprovalGateway: PAUSED - awaiting manager review")
        await ctx.request_info(
            request_data=ManagerApprovalRequest(
                request={**request, "escalation_reasons": reasons},
                prompt=(f"{request['request_id']} | {request['product']} | "
                        f"INR {request['amount_inr']:,} | Risk: {request['risk_level']}"),
            ),
            response_type=str,
        )

    @response_handler
    async def on_manager_decision(self, original_request: ManagerApprovalRequest,
                                  response: str, ctx: WorkflowContext[dict]) -> None:
        # RESUME: the original request comes back with the manager's answer.
        # Anything other than "approve" is treated as a rejection (fail-safe).
        approved = response.strip().lower() == "approve"
        print(f"  ApprovalGateway: RESUMED - manager chose {'approve' if approved else 'reject'}")
        await ctx.send_message({**original_request.request, "approval_route": "Human Review",
                                "final_decision": "MANAGER_APPROVED" if approved else "MANAGER_REJECTED"})


# =====================================================
# 4. AGENTS AND WORKFLOW GRAPH (Tasks 2 and 4)
# =====================================================

POLICY_TEXT = (
    "Return policy (demo): automatic approval needs ALL of: amount below INR 25,000; "
    "request within 30 days of delivery; invoice available; item unopened, or damaged "
    "with supporting photographs; fewer than 3 previous returns in 90 days; no HIGH risk."
)


def build_workflow(chat_client: OpenAIChatClient):

    eligibility_agent = Agent(
        client=chat_client,
        name="EligibilityAgent",
        instructions=(
            "You are the Eligibility Agent for an e-commerce returns team. " + POLICY_TEXT +
            " You receive a return request and 'policy_issues', the result of the company's "
            "automatic policy checks. In 2-3 sentences, say whether the request meets the policy "
            "and explain each listed exception. Use only the supplied facts. Do not decide "
            "approval and do not contradict policy_issues."
        ),
    )

    risk_agent = Agent(
        client=chat_client,
        name="RiskAgent",
        instructions=(
            "You are the Risk Agent for an e-commerce returns team. Assess risk using only the "
            "supplied data. Concerns: unusual return frequency (3 or more previous returns in "
            "90 days), missing invoice or missing photo evidence for a damaged item, high value "
            "(INR 25,000 or more), or a return reason that does not fit the item condition. "
            "Reply in exactly this form: 'HIGH - <one sentence>' or 'LOW - <one sentence>'. "
            "Use HIGH only when at least one concern is present; otherwise LOW."
        ),
    )

    response_agent = Agent(
        client=chat_client,
        name="CustomerResponseAgent",
        instructions=(
            "You write a short, polite customer message (3-4 sentences) starting 'Dear Customer,'. "
            "Communicate the decision in 'final_decision' exactly; you cannot change it. "
            "AUTO_APPROVED or MANAGER_APPROVED: say the request is approved and the next steps "
            "will follow. MANAGER_REJECTED: say it could not be approved and briefly why. "
            "Never say a refund or replacement has already been processed, issued, credited or "
            "shipped. No placeholders such as [Name]."
        ),
    )

    # ---------- EXECUTOR 1: ELIGIBILITY ----------
    @executor(id="eligibility_review")
    async def eligibility_review(request: dict, ctx: WorkflowContext[dict]) -> None:
        issues = check_policy(request)   # Python decides
        print(f"  EligibilityAgent: {len(issues)} policy issue(s) found")
        result = await eligibility_agent.run(json.dumps({**request, "policy_issues": issues}))
        await ctx.send_message({**request, "eligibility_issues": issues,
                                "eligibility_findings": result.text.strip()})

    # ---------- EXECUTOR 2: RISK ----------
    @executor(id="risk_review")
    async def risk_review(request: dict, ctx: WorkflowContext[dict]) -> None:
        result = await risk_agent.run(json.dumps(request))
        level, summary = parse_risk(result.text)
        print(f"  RiskAgent: {level}")
        await ctx.send_message({**request, "risk_level": level, "risk_assessment": summary})

    # ---------- EXECUTOR 3: CUSTOMER RESPONSE + FINAL OUTPUT ----------
    @executor(id="customer_response")
    async def customer_response(request: dict, ctx: WorkflowContext[Never, dict]) -> None:
        print("  CustomerResponseAgent: drafting message")
        result = await response_agent.run(json.dumps(request))

        # Task 6: the structured final record
        await ctx.yield_output({
            "request_id": request["request_id"],
            "order_id": request["order_id"],
            "product": request["product"],
            "request_type": request["request_type"],
            "requested_amount_inr": request["amount_inr"],
            "eligibility_findings": {
                "policy_issues": request["eligibility_issues"],
                "summary": request["eligibility_findings"],
            },
            "risk_assessment": {
                "level": request["risk_level"],
                "summary": request["risk_assessment"],
            },
            "approval_route": request["approval_route"],
            "final_decision": request["final_decision"],
            "customer_message_draft": safe_customer_message(result.text.strip(), request),
        })

    # ---------- THE GRAPH ----------
    gateway = ApprovalGateway()
    return (
        WorkflowBuilder(start_executor=eligibility_review)
        .add_edge(eligibility_review, risk_review)
        .add_edge(risk_review, gateway)
        .add_edge(gateway, customer_response)
        .build()
    )


# =====================================================
# 5. RUN ONE REQUEST, PAUSING FOR THE MANAGER (Task 5)
# =====================================================

def ask_manager(approval: ManagerApprovalRequest) -> str:
    """Show the escalated request and keep asking until the answer is approve or reject."""
    request = approval.request
    print("\n" + "=" * 60)
    print("MANAGER APPROVAL REQUIRED")
    print(f"Request ID : {request['request_id']}  (order {request['order_id']})")
    print(f"Item       : {request['product']} ({request['product_category']}) - {request['request_type']}")
    print(f"Amount     : INR {request['amount_inr']:,}")
    print("Eligibility issues:")
    for issue in request["eligibility_issues"] or ["None"]:
        print(f"  - {issue}")
    print(f"Risk       : {request['risk_level']} - {request['risk_assessment']}")
    print(f"Escalated because: {'; '.join(request['escalation_reasons'])}")

    while True:
        answer = input("Type approve or reject: ").strip().lower()
        if answer in ("approve", "reject"):
            return answer
        print(f"  Invalid input '{answer}'. Please type exactly approve or reject.")


async def run_one(workflow, request: dict) -> dict:
    """Run the graph for one request; pause and resume as many times as needed."""
    stream = workflow.run(request, stream=True)

    while True:
        pending, output = {}, None

        async for event in stream:
            if event.type == "request_info":       # the gateway paused
                pending[event.request_id] = event.data
            elif event.type == "output":           # the final record
                output = event.data

        if output is not None:
            return output
        if not pending:
            raise RuntimeError("Workflow stopped without output or approval request")

        # Collect the manager's answers, then RESUME the same workflow with them
        responses = {request_id: ask_manager(approval) for request_id, approval in pending.items()}
        stream = workflow.run(stream=True, responses=responses)


# =====================================================
# 6. MAIN
# =====================================================

async def main() -> None:
    config = check_config()
    requests = load_requests()
    print(f"Loaded {len(requests)} return requests from returns.json")

    results = []
    async with AsyncOpenAI(api_key=config["AZURE_OPENAI_API_KEY"],
                           base_url=config["AZURE_OPENAI_BASE_URL"]) as client:
        chat_client = OpenAIChatClient(model=config["AZURE_OPENAI_MODEL"], async_client=client)

        for request in requests:
            print("\n" + "#" * 60)
            print(f"REQUEST {request['request_id']}: {request['product']}")
            workflow = build_workflow(chat_client)   # fresh graph state per request
            output = await run_one(workflow, request)
            print("\nFINAL RECORD")
            print(json.dumps(output, indent=2, ensure_ascii=False))
            results.append(output)

    # One-line-per-request summary for the screenshots (Task 7)
    print("\n" + "=" * 60 + "\nSUMMARY")
    for result in results:
        print(f"  {result['request_id']:<10} {result['approval_route']:<13} {result['final_decision']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ChatClientException as error:
        # e.g. 404 = AZURE_OPENAI_MODEL is not a deployment name on this resource
        sys.exit(f"AZURE OPENAI ERROR: {error}\nCheck AZURE_OPENAI_BASE_URL, the API key, "
                 "and that AZURE_OPENAI_MODEL is your deployment's exact name.")
