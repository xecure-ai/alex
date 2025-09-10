"""
Financial Planner Orchestrator Agent - coordinates portfolio analysis across specialized agents.
"""

import os
import json
import boto3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from agents import function_tool
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger(__name__)

# Initialize Lambda client
lambda_client = boto3.client("lambda")

# Lambda function names from environment
TAGGER_FUNCTION = os.getenv("TAGGER_FUNCTION", "alex-tagger")
REPORTER_FUNCTION = os.getenv("REPORTER_FUNCTION", "alex-reporter")
CHARTER_FUNCTION = os.getenv("CHARTER_FUNCTION", "alex-charter")
RETIREMENT_FUNCTION = os.getenv("RETIREMENT_FUNCTION", "alex-retirement")
MOCK_LAMBDAS = os.getenv("MOCK_LAMBDAS", "false").lower() == "true"


async def invoke_lambda_agent(
    agent_name: str, function_name: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke a Lambda function for an agent."""

    # For local testing with mocked agents
    if MOCK_LAMBDAS:
        logger.info(f"[MOCK] Would invoke {agent_name} with payload: {json.dumps(payload)[:200]}")
        return {"success": True, "message": f"[Mock] {agent_name} completed", "mock": True}

    try:
        logger.info(f"Invoking {agent_name} Lambda: {function_name}")

        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        result = json.loads(response["Payload"].read())

        # Unwrap Lambda response if it has the standard format
        if isinstance(result, dict) and "statusCode" in result and "body" in result:
            if isinstance(result["body"], str):
                try:
                    result = json.loads(result["body"])
                except json.JSONDecodeError:
                    result = {"message": result["body"]}
            else:
                result = result["body"]

        logger.info(f"{agent_name} completed successfully")
        return result

    except Exception as e:
        logger.error(f"Error invoking {agent_name}: {e}")
        return {"error": str(e)}


def handle_missing_instruments(job_id: str, db) -> None:
    """
    Check for and tag any instruments missing allocation data.
    This is done automatically before the agent runs.
    """
    logger.info("Planner: Checking for instruments missing allocation data...")

    # Get job and portfolio data
    job = db.jobs.find_by_id(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return

    user_id = job["clerk_user_id"]
    accounts = db.accounts.find_by_user(user_id)

    missing = []
    for account in accounts:
        positions = db.positions.find_by_account(account["id"])
        for position in positions:
            instrument = db.instruments.find_by_symbol(position["symbol"])
            if instrument:
                has_allocations = bool(
                    instrument.get("allocation_regions")
                    and instrument.get("allocation_sectors")
                    and instrument.get("allocation_asset_class")
                )
                if not has_allocations:
                    missing.append(
                        {"symbol": position["symbol"], "name": instrument.get("name", "")}
                    )
            else:
                missing.append({"symbol": position["symbol"], "name": ""})

    if missing:
        logger.info(
            f"Planner: Found {len(missing)} instruments needing classification: {[m['symbol'] for m in missing]}"
        )

        try:
            response = lambda_client.invoke(
                FunctionName=TAGGER_FUNCTION,
                InvocationType="RequestResponse",
                Payload=json.dumps({"instruments": missing}),
            )

            result = json.loads(response["Payload"].read())

            if isinstance(result, dict) and "statusCode" in result:
                if result["statusCode"] == 200:
                    logger.info(
                        f"Planner: InstrumentTagger completed - Tagged {len(missing)} instruments"
                    )
                else:
                    logger.error(
                        f"Planner: InstrumentTagger failed with status {result['statusCode']}"
                    )

        except Exception as e:
            logger.error(f"Planner: Error tagging instruments: {e}")
    else:
        logger.info("Planner: All instruments have allocation data")


def load_portfolio_summary(job_id: str, db) -> Dict[str, Any]:
    """Load portfolio summary data for the agent."""
    try:
        job = db.jobs.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        user_id = job["clerk_user_id"]
        user = db.users.find_by_clerk_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        accounts = db.accounts.find_by_user(user_id)

        portfolio_data = {
            "user_id": user_id,
            "job_id": job_id,
            "years_until_retirement": user.get("years_until_retirement", 30),
            "target_retirement_income": float(user.get("target_retirement_income", 80000)),
            "accounts": [],
        }

        for account in accounts:
            positions = db.positions.find_by_account(account["id"])
            account_data = {
                "id": account["id"],
                "name": account["account_name"],
                "cash_balance": float(account.get("cash_balance", 0)),
                "positions": [],
            }

            for position in positions:
                instrument = db.instruments.find_by_symbol(position["symbol"])
                if instrument:
                    account_data["positions"].append(
                        {
                            "symbol": position["symbol"],
                            "quantity": float(position["quantity"]),
                            "instrument": instrument,
                        }
                    )

            portfolio_data["accounts"].append(account_data)

        return portfolio_data

    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        raise


async def invoke_reporter_internal(job_id: str) -> str:
    """
    Invoke the Report Writer Lambda to generate portfolio analysis narrative.

    Args:
        job_id: The job ID for the analysis

    Returns:
        Confirmation message
    """
    result = await invoke_lambda_agent("Reporter", REPORTER_FUNCTION, {"job_id": job_id})

    if "error" in result:
        return f"Reporter agent failed: {result['error']}"

    return "Reporter agent completed successfully. Portfolio analysis narrative has been generated and saved."


async def invoke_charter_internal(job_id: str, portfolio_data: Dict[str, Any]) -> str:
    """
    Invoke the Chart Maker Lambda to create portfolio visualizations.

    Args:
        job_id: The job ID for the analysis
        portfolio_data: The portfolio data for visualization

    Returns:
        Confirmation message
    """
    result = await invoke_lambda_agent(
        "Charter", CHARTER_FUNCTION, {"job_id": job_id, "portfolio_data": portfolio_data}
    )

    if "error" in result:
        return f"Charter agent failed: {result['error']}"

    return "Charter agent completed successfully. Portfolio visualizations have been created and saved."


async def invoke_retirement_internal(job_id: str) -> str:
    """
    Invoke the Retirement Specialist Lambda for retirement projections.

    Args:
        job_id: The job ID for the analysis

    Returns:
        Confirmation message
    """
    result = await invoke_lambda_agent("Retirement", RETIREMENT_FUNCTION, {"job_id": job_id})

    if "error" in result:
        return f"Retirement agent failed: {result['error']}"

    return "Retirement agent completed successfully. Retirement projections have been calculated and saved."


async def finalize_job_internal(
    job_id: str, summary: str, key_findings: List[str], recommendations: List[str], db
) -> str:
    """
    Finalize the job with the orchestrator's summary and mark it as completed.

    Args:
        job_id: The job ID to finalize
        summary: Executive summary of the analysis
        key_findings: List of key findings from all agents
        recommendations: List of actionable recommendations
        db: Database connection

    Returns:
        Confirmation message
    """
    try:
        # Save the orchestrator's summary to the database
        summary_payload = {
            "summary": summary,
            "key_findings": key_findings,
            "recommendations": recommendations,
            "completed_at": datetime.utcnow().isoformat(),
        }

        # Update summary first
        success = db.jobs.update_summary(job_id, summary_payload)

        if success:
            # Then update status to completed
            success = db.jobs.update_status(job_id, "completed")

        if success:
            logger.info(f"Planner: Job {job_id} finalized successfully")
            return f"Job {job_id} has been finalized and marked as completed."
        else:
            return f"Failed to finalize job {job_id}"

    except Exception as e:
        logger.error(f"Planner: Error finalizing job: {e}")
        return f"Failed to finalize job: {str(e)}"


def create_agent(job_id: str, portfolio_data: Dict[str, Any], db):
    """Create the orchestrator agent with tools."""

    # Get model configuration
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    # Set region for LiteLLM Bedrock calls
    bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")
    os.environ["AWS_REGION_NAME"] = bedrock_region

    model = LitellmModel(model=f"bedrock/{model_id}")

    # Calculate portfolio summary for context
    total_value = 0
    total_positions = 0

    for account in portfolio_data.get("accounts", []):
        total_value += account.get("cash_balance", 0)
        for position in account.get("positions", []):
            total_positions += 1
            instrument = position.get("instrument", {})
            price = float(instrument.get("current_price", 100))
            total_value += float(position.get("quantity", 0)) * price

    # Bind job_id and data to tools
    async def reporter() -> str:
        """Invoke the Report Writer agent to generate portfolio analysis narrative."""
        return await invoke_reporter_internal(job_id)

    async def charter() -> str:
        """Invoke the Chart Maker agent to create portfolio visualizations."""
        return await invoke_charter_internal(job_id, portfolio_data)

    async def retirement() -> str:
        """Invoke the Retirement Specialist agent for retirement projections."""
        return await invoke_retirement_internal(job_id)

    async def finalize(summary: str, key_findings: List[str], recommendations: List[str]) -> str:
        """Finalize the job with summary and mark as completed."""
        return await finalize_job_internal(job_id, summary, key_findings, recommendations, db)

    reporter.__name__ = "invoke_reporter"
    charter.__name__ = "invoke_charter"
    retirement.__name__ = "invoke_retirement"
    finalize.__name__ = "finalize_job"

    tools = [
        function_tool(reporter),
        function_tool(charter),
        function_tool(retirement),
        function_tool(finalize),
    ]

    # Create task context
    task = f"""You are orchestrating a comprehensive portfolio analysis for job {job_id}.

Portfolio Overview:
- Total Value: ${total_value:,.2f}
- Number of Accounts: {len(portfolio_data.get("accounts", []))}
- Number of Positions: {total_positions}
- Years to Retirement: {portfolio_data.get("years_until_retirement", "Unknown")}
- Target Retirement Income: ${portfolio_data.get("target_retirement_income", 0):,.0f}

Your task is to coordinate a comprehensive financial analysis by:

1. ALWAYS invoke the Report Writer agent to generate a detailed portfolio analysis narrative
2. ALWAYS invoke the Chart Maker agent to create visualizations of the portfolio
3. Consider whether retirement planning analysis would be valuable (usually yes if retirement goals are set)
4. After all agents complete, finalize the job with:
   - An executive summary synthesizing all findings
   - Key findings list (3-5 items)
   - Actionable recommendations list (3-5 items)

Use your judgment to determine which agents to invoke based on the portfolio characteristics.
A simple portfolio might not need all agents, while a complex one benefits from comprehensive analysis.

Remember: Each agent saves its own results to the database. You're coordinating them and providing the synthesis."""

    return model, tools, task
