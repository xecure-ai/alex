# Guide 8: Enterprise Grade - Scalability, Security, Monitoring, Guardrails & Observability

Welcome to the final guide in the Alex Financial Advisor deployment series! In this guide, we'll transform our application into a production-ready, enterprise-grade system by implementing best practices for scalability, security, monitoring, guardrails, explainability, and observability.

By the end of this guide, your Alex Financial Advisor will be:
- **Scalable**: Ready to handle enterprise-level traffic
- **Secure**: Protected with multiple layers of security
- **Monitored**: Full visibility into system health and performance
- **Guarded**: Protected against AI hallucinations and errors
- **Explainable**: Transparent AI decision-making
- **Observable**: Complete tracing of all agent interactions

## Section 1: Scalability

Our serverless architecture is already designed for automatic scaling, but let's explore how to configure it for enterprise-level traffic.

### Understanding Serverless Scalability

The beauty of our serverless architecture is that AWS automatically scales components based on demand:

1. **Lambda Functions** scale automatically:
   - Concurrent executions: Default 1,000 (can be increased to 10,000+)
   - Each agent can handle multiple requests simultaneously
   - No server management required

2. **Aurora Serverless v2** scales automatically:
   - From 0.5 to 1 ACU (Aurora Capacity Units) by default
   - Can scale up to 128 ACUs for high traffic
   - Scales in ~15 seconds based on load

3. **API Gateway** handles millions of requests:
   - Default throttle: 10,000 requests/second
   - Burst: 5,000 requests
   - Can be increased via AWS support

4. **SQS** provides unlimited throughput:
   - Standard queues: Nearly unlimited TPS
   - FIFO queues: 300 messages/second (can batch to 3,000)

### Configuring for Higher Scale

To prepare for enterprise traffic, you can adjust these settings in the Terraform configurations:

**In `terraform/5_database/main.tf`:**
```hcl
resource "aws_rds_cluster" "aurora" {
  # Increase max capacity for high traffic
  serverlessv2_scaling_configuration {
    max_capacity = 16  # Increase from 1 to 16 ACUs
    min_capacity = 0.5 # Keep minimum low for cost efficiency
  }
}
```

**In `terraform/6_agents/main.tf`:**
```hcl
resource "aws_lambda_function" "planner" {
  # Increase memory for faster processing
  memory_size = 10240  # Increase from 3072 to 10GB
  timeout     = 900    # Keep at 15 minutes max

  # Add reserved concurrent executions for guaranteed capacity
  reserved_concurrent_executions = 100  # Guarantee 100 concurrent
}
```

**In `terraform/7_frontend/main.tf`:**
```hcl
resource "aws_apigatewayv2_stage" "api" {
  # Configure throttling for protection
  default_route_settings {
    throttle_rate_limit  = 10000  # Requests per second
    throttle_burst_limit = 5000   # Burst capacity
  }
}
```

### Load Testing Your Application

Before going to production, test your scalability:

```bash
# Install Apache Bench
apt-get install apache2-utils  # Ubuntu/Debian
brew install apache2-utils     # macOS

# Test API endpoint (replace with your API URL)
ab -n 1000 -c 50 -H "Authorization: Bearer YOUR_TOKEN" \
   https://your-api.execute-api.region.amazonaws.com/api/user
```

### Cost Optimization at Scale

Monitor and optimize costs as you scale:

1. **Use AWS Cost Explorer** to track spending
2. **Set up billing alerts** for unexpected costs
3. **Implement caching** with CloudFront for static content
4. **Use SQS Dead Letter Queues** to handle failed messages
5. **Consider Step Functions** for complex orchestrations at scale

## Section 2: Security

Our application already implements multiple security best practices. Let's review them and explore additional enterprise security features.

### Current Security Implementation

#### 1. **IAM Least Privilege Access**
Each Lambda function has minimal required permissions:

```hcl
# In terraform/6_agents/main.tf
resource "aws_iam_role_policy" "planner_policy" {
  policy = jsonencode({
    Statement = [
      {
        Effect = "Allow"
        Action = ["rds-data:ExecuteStatement", "rds-data:BatchExecuteStatement"]
        Resource = "arn:aws:rds-db:*:*:cluster:alex-database"
      },
      {
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = [
          "arn:aws:lambda:*:*:function:alex-tagger",
          "arn:aws:lambda:*:*:function:alex-reporter",
          "arn:aws:lambda:*:*:function:alex-charter",
          "arn:aws:lambda:*:*:function:alex-retirement"
        ]
      }
    ]
  })
}
```

#### 2. **JWT Authentication with Clerk**
All API calls require valid JWT tokens:
- Tokens expire after 1 hour
- JWKS endpoint for key rotation
- User context validated on every request

#### 3. **API Gateway Throttling**
Protection against DDoS and abuse:
```hcl
throttle_rate_limit  = 100   # 100 requests per second per user
throttle_burst_limit = 200   # Burst capacity
```

#### 4. **CORS Controls**
Strict CORS configuration:
- Origin validation
- Credentials not allowed with wildcard origins
- Preflight caching for performance

#### 5. **XSS Protection**
Content Security Policy headers:
```javascript
// In frontend pages
<meta httpEquiv="Content-Security-Policy"
      content="default-src 'self'; script-src 'self' 'unsafe-inline' https://clerk.com; style-src 'self' 'unsafe-inline';" />
```

#### 6. **Secrets Management**
Using AWS Secrets Manager:
- Database credentials never in code
- Automatic rotation capability
- Encrypted at rest with KMS

### Additional Enterprise Security Features

To further enhance security, consider implementing:

#### 1. **AWS WAF (Web Application Firewall)**
Add to `terraform/7_frontend/main.tf`:
```hcl
resource "aws_wafv2_web_acl" "api_protection" {
  name  = "alex-api-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "RateLimitRule"
    priority = 1

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    action {
      block {}
    }
  }

  rule {
    name     = "SQLiRule"
    priority = 2

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesSQLiRuleSet"
      }
    }

    override_action {
      none {}
    }
  }
}
```

#### 2. **VPC Endpoints for Private Communication**
Keep traffic within AWS network:
```hcl
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.region.s3"
}
```

#### 3. **AWS GuardDuty for Threat Detection**
```hcl
resource "aws_guardduty_detector" "main" {
  enable = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"
}
```

#### 4. **Parameter Validation**
Add to Lambda functions:
```python
from pydantic import validator
import re

class PositionCreate(BaseModel):
    symbol: str

    @validator('symbol')
    def validate_symbol(cls, v):
        if not re.match(r'^[A-Z]{1,5}$', v):
            raise ValueError('Invalid symbol format')
        return v
```

## Section 3: Monitoring

Let's enhance our logging and create comprehensive CloudWatch dashboards to monitor our application.

### Enhanced Logging Implementation

First, let's ensure our agents and API have comprehensive logging:

**For the API (backend/api/main.py):**
```python
import logging
import json
from datetime import datetime

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class StructuredLogger:
    @staticmethod
    def log_event(event_type, user_id=None, details=None):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "details": details
        }
        logger.info(json.dumps(log_entry))

# Add to endpoints
@app.post("/api/analyze")
async def trigger_analysis(user=Depends(clerk_guard)):
    StructuredLogger.log_event(
        "ANALYSIS_TRIGGERED",
        user_id=user.clerk_user_id,
        details={"accounts": len(accounts)}
    )
    # ... rest of endpoint
```

**For agents (example in backend/planner/lambda_handler.py):**
```python
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # Log incoming request
    logger.info(json.dumps({
        "event": "PLANNER_STARTED",
        "job_id": job_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }))

    # Log agent delegations
    for agent in ["reporter", "charter", "retirement"]:
        logger.info(json.dumps({
            "event": "AGENT_INVOKED",
            "agent": agent,
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat()
        }))

    # Log completion
    logger.info(json.dumps({
        "event": "PLANNER_COMPLETED",
        "job_id": job_id,
        "duration_seconds": duration,
        "status": "success"
    }))
```

### Creating CloudWatch Dashboards

Navigate to AWS CloudWatch Console and create a dashboard with these widgets:

#### 1. **API Activity Dashboard**
```json
{
  "widgets": [
    {
      "type": "log",
      "properties": {
        "query": "SOURCE '/aws/lambda/alex-api' | fields @timestamp, event_type, user_id | filter event_type = 'USER_LOGIN' | stats count() by bin(5m)",
        "region": "us-east-1",
        "title": "User Logins Over Time"
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "SOURCE '/aws/lambda/alex-api' | filter event_type = 'ANALYSIS_TRIGGERED' | stats count() by user_id",
        "region": "us-east-1",
        "title": "Analyses by User"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
          [".", "Errors", {"stat": "Sum"}],
          [".", "Duration", {"stat": "Average"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "API Lambda Metrics"
      }
    }
  ]
}
```

#### 2. **Agent Performance Dashboard**
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Duration", {"label": "Planner", "dimensions": {"FunctionName": "alex-planner"}}],
          [".", ".", {"label": "Reporter", "dimensions": {"FunctionName": "alex-reporter"}}],
          [".", ".", {"label": "Charter", "dimensions": {"FunctionName": "alex-charter"}}],
          [".", ".", {"label": "Retirement", "dimensions": {"FunctionName": "alex-retirement"}}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Agent Execution Times"
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "SOURCE '/aws/lambda/alex-planner' | filter event = 'AGENT_INVOKED' | stats count() by agent",
        "region": "us-east-1",
        "title": "Agent Invocation Counts"
      }
    }
  ]
}
```

#### 3. **SQS Queue Monitoring**
Navigate to SQS console to view:
- Messages in flight
- Message age
- Dead letter queue messages
- Throughput metrics

### Setting Up CloudWatch Alarms

Create alarms for critical metrics:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "alex-api-errors" \
  --alarm-description "Alert when API has errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=alex-api
```

### Cost Monitoring

Set up AWS Cost Explorer alerts:
1. Navigate to AWS Billing Dashboard
2. Create a budget for your expected monthly spend
3. Set alerts at 50%, 80%, and 100% of budget
4. Configure SNS notifications to your email

## Section 4: Guardrails

Implement validation and safety checks to prevent AI errors from affecting users.

### Charter Agent Output Validation

Add this validation code to `backend/charter/agent.py` to ensure well-formed JSON output:

```python
import json
import logging
from typing import Dict, Any

logger = logging.getLogger()

def validate_chart_data(chart_json: str) -> tuple[bool, str, Dict[Any, Any]]:
    """
    Validates that charter agent output is well-formed JSON with expected structure.
    Returns (is_valid, error_message, parsed_data)
    """
    try:
        # Parse JSON
        data = json.loads(chart_json)

        # Validate expected structure
        required_keys = ["charts"]
        if not all(key in data for key in required_keys):
            return False, f"Missing required keys. Expected: {required_keys}", {}

        # Validate charts array
        if not isinstance(data["charts"], list):
            return False, "Charts must be an array", {}

        # Validate each chart
        for i, chart in enumerate(data["charts"]):
            if "type" not in chart:
                return False, f"Chart {i} missing 'type' field", {}

            if "data" not in chart:
                return False, f"Chart {i} missing 'data' field", {}

            # Validate chart data is array
            if not isinstance(chart["data"], list):
                return False, f"Chart {i} data must be an array", {}

            # Validate data points have required fields based on chart type
            if chart["type"] == "pie":
                for point in chart["data"]:
                    if "name" not in point or "value" not in point:
                        return False, f"Pie chart data points must have 'name' and 'value'", {}
            elif chart["type"] == "bar":
                for point in chart["data"]:
                    if "category" not in point:
                        return False, f"Bar chart data points must have 'category'", {}

        return True, "", data

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from charter agent: {e}")
        return False, f"Invalid JSON: {e}", {}
    except Exception as e:
        logger.error(f"Unexpected error validating chart data: {e}")
        return False, f"Validation error: {e}", {}

# Use in your charter agent:
async def run_charter_agent(job_id: str, task: str) -> str:
    # ... existing agent code ...

    result = await Runner.run(agent, input=task, max_turns=10)

    # Validate output
    is_valid, error_msg, parsed_data = validate_chart_data(result.final_output)

    if not is_valid:
        logger.error(f"Charter agent produced invalid output for job {job_id}: {error_msg}")
        # Return safe fallback
        return json.dumps({
            "charts": [],
            "error": "Unable to generate charts at this time"
        })

    return json.dumps(parsed_data)
```

### Input Validation Guardrails

Add to all agents to prevent prompt injection:

```python
def sanitize_user_input(text: str) -> str:
    """Remove potential prompt injection attempts"""
    # Remove common injection patterns
    dangerous_patterns = [
        "ignore previous instructions",
        "disregard all prior",
        "forget everything",
        "new instructions:",
        "system:",
        "assistant:"
    ]

    text_lower = text.lower()
    for pattern in dangerous_patterns:
        if pattern in text_lower:
            logger.warning(f"Potential prompt injection detected: {pattern}")
            return "[INVALID INPUT DETECTED]"

    return text

# Use when processing user data
user_goals = sanitize_user_input(user.retirement_goals or "")
```

### Response Size Limits

Prevent runaway token usage:

```python
def truncate_response(text: str, max_length: int = 50000) -> str:
    """Ensure responses don't exceed reasonable size"""
    if len(text) > max_length:
        logger.warning(f"Response truncated from {len(text)} to {max_length} characters")
        return text[:max_length] + "\n\n[Response truncated due to length]"
    return text
```

### Retry Logic with Exponential Backoff

Add resilience to agent invocations:

```python
import asyncio
from typing import Optional

async def invoke_agent_with_retry(
    agent_name: str,
    payload: dict,
    max_retries: int = 3
) -> Optional[dict]:
    """Invoke agent with exponential backoff retry"""

    for attempt in range(max_retries):
        try:
            response = await lambda_client.invoke(
                FunctionName=f"alex-{agent_name}",
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            return json.loads(response['Payload'].read())

        except Exception as e:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(f"Agent {agent_name} failed (attempt {attempt + 1}): {e}")

            if attempt < max_retries - 1:
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Agent {agent_name} failed after {max_retries} attempts")
                return None
```

## Section 5: Explainability

Modern LLMs and agentic systems provide unprecedented transparency compared to traditional black-box AI. Let's implement explainability features to help users understand AI decision-making.

### The Evolution of Explainable AI

In the early days of deep learning, neural networks were often criticized as "black boxes" - systems that produced outputs without clear reasoning. This was a serious concern in regulated industries like finance and healthcare.

Modern Large Language Models (LLMs) and agentic systems address this concern through:
1. **Natural language explanations** - AI can explain its reasoning in plain English
2. **Chain-of-thought reasoning** - Step-by-step problem solving that's auditable
3. **Structured outputs** - Predictable, parseable responses with clear logic
4. **Prompt transparency** - The instructions given to AI are visible and modifiable

### Implementing Explainability in the Tagger Agent

Let's modify the Tagger agent to include rationale for its decisions. Add this to `backend/tagger/agent.py`:

```python
from pydantic import BaseModel, Field
from typing import Dict

class InstrumentClassificationWithRationale(BaseModel):
    # Rationale MUST come first so LLM generates reasoning before answers
    rationale: str = Field(
        description="Detailed explanation of why these classifications were chosen, including specific factors considered"
    )

    asset_class: AssetClassType = Field(
        description="Primary asset class classification"
    )

    asset_class_allocation: Dict[str, float] = Field(
        description="Percentage breakdown by asset class",
        example={"equity": 100.0}
    )

    region_allocation: Dict[str, float] = Field(
        description="Percentage breakdown by geographic region",
        example={"north_america": 70.0, "europe": 20.0, "asia_pacific": 10.0}
    )

    sector_allocation: Dict[str, float] = Field(
        description="Percentage breakdown by sector (only for equity)",
        example={"technology": 30.0, "healthcare": 20.0, "financial": 50.0}
    )

# In your tagger agent function:
async def run_tagger_agent(instrument: dict) -> dict:
    model = LitellmModel(model=f"bedrock/{bedrock_model}")

    with trace("Classify instrument with explainability"):
        agent = Agent(
            name="Instrument Tagger with Explainability",
            instructions=CLASSIFICATION_INSTRUCTIONS,
            model=model,
            response_format=InstrumentClassificationWithRationale
        )

        result = await Runner.run(
            agent,
            input=create_classification_task(instrument),
            max_turns=1
        )

        classification = result.final_output_as(InstrumentClassificationWithRationale)

        # Log the rationale for audit trail
        logger.info(json.dumps({
            "event": "CLASSIFICATION_RATIONALE",
            "symbol": instrument["symbol"],
            "rationale": classification.rationale,
            "timestamp": datetime.utcnow().isoformat()
        }))

        # Return classification without rationale to planner
        return {
            "asset_class": classification.asset_class,
            "asset_class_allocation": classification.asset_class_allocation,
            "region_allocation": classification.region_allocation,
            "sector_allocation": classification.sector_allocation
        }
```

### Adding Explainability to Portfolio Recommendations

For the Reporter agent, include reasoning in recommendations:

```python
# In templates.py
ANALYSIS_INSTRUCTIONS_WITH_EXPLANATION = """
When providing recommendations, always:
1. Start with your reasoning process
2. List specific factors you considered
3. Explain why certain recommendations were prioritized
4. Include any assumptions made
5. Note any limitations or caveats

Format each recommendation as:
**Recommendation:** [The action to take]
**Reasoning:** [Why this recommendation was made]
**Impact:** [Expected outcome if implemented]
**Priority:** [High/Medium/Low based on user goals]
"""
```

### Audit Trail for Compliance

Create a comprehensive audit log for all AI decisions:

```python
class AuditLogger:
    @staticmethod
    def log_ai_decision(
        agent_name: str,
        job_id: str,
        input_data: dict,
        output_data: dict,
        model_used: str,
        duration_ms: int
    ):
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "job_id": job_id,
            "model": model_used,
            "input_hash": hashlib.sha256(
                json.dumps(input_data, sort_keys=True).encode()
            ).hexdigest(),
            "output_summary": {
                "type": type(output_data).__name__,
                "size_bytes": len(json.dumps(output_data))
            },
            "duration_ms": duration_ms,
            "compliance_check": "PASS"  # Add actual compliance logic
        }

        # Store in CloudWatch for long-term retention
        logger.info(json.dumps(audit_entry))

        # Could also store in DynamoDB for querying
        return audit_entry
```

## Section 6: Observability with LangFuse

LangFuse provides comprehensive tracing for LLM applications, giving you visibility into agent interactions, token usage, and performance metrics.

### Setting Up LangFuse Integration

First, let's modify our agents to support LangFuse when credentials are provided. This integration will be transparent - if LangFuse credentials aren't set, the agents work normally.

**Step 1: Update Agent Dependencies**

Add LangFuse to each agent's `pyproject.toml`:
```toml
# In backend/planner/pyproject.toml (and all other agents)
dependencies = [
    "openai-agents[litellm,langfuse]",  # Add langfuse extra
    # ... other dependencies
]
```

**Step 2: Create LangFuse Integration Module**

Create `backend/shared/observability.py`:
```python
import os
from typing import Optional
from agents import trace
from agents.extensions.integrations.langfuse import LangfuseIntegration

def setup_langfuse() -> Optional[LangfuseIntegration]:
    """
    Set up LangFuse integration if credentials are available.
    Returns None if credentials not set, allowing agents to run normally.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if public_key and secret_key:
        return LangfuseIntegration(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            flush_at=1,  # Flush immediately for Lambda
            flush_interval=0.5
        )
    return None
```

**Step 3: Integrate into Each Agent**

Update each agent to use LangFuse when available. Example for `backend/planner/agent.py`:

```python
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.observability import setup_langfuse
from agents import Agent, Runner, trace, function_tool
from agents.extensions.models.litellm_model import LitellmModel

async def run_planner_agent(job_id: str, user_data: dict, accounts: list) -> dict:
    # Set up observability if available
    langfuse = setup_langfuse()

    # Create comprehensive trace metadata
    trace_metadata = {
        "job_id": job_id,
        "user_id": user_data.get("clerk_user_id"),
        "agent": "planner",
        "account_count": len(accounts),
        "total_value": sum(a.get("total_value", 0) for a in accounts)
    }

    # Use trace with metadata for better observability
    with trace(
        "Portfolio Analysis Orchestration",
        metadata=trace_metadata,
        integration=langfuse  # Will be None if not configured
    ):
        model = LitellmModel(
            model=f"bedrock/{os.getenv('BEDROCK_MODEL_ID')}",
            aws_region=os.getenv("BEDROCK_REGION", "us-east-1")
        )

        # Add session tags for filtering in LangFuse
        if langfuse:
            langfuse.set_tags([
                f"env:{os.getenv('ENVIRONMENT', 'production')}",
                f"version:{os.getenv('AGENT_VERSION', '1.0')}",
                "agent:planner"
            ])

        agent = Agent(
            name="Financial Planning Orchestrator",
            instructions=PLANNER_INSTRUCTIONS,
            model=model,
            tools=[delegate_to_agent, fetch_market_knowledge]
        )

        # Create detailed task with context
        task = create_analysis_task(user_data, accounts)

        # Run with comprehensive tracing
        result = await Runner.run(
            agent,
            input=task,
            max_turns=20,
            session_id=job_id  # Links all traces to this job
        )

        # Log token usage if available
        if hasattr(result, 'usage'):
            logger.info(json.dumps({
                "event": "TOKEN_USAGE",
                "job_id": job_id,
                "agent": "planner",
                "total_tokens": result.usage.total_tokens,
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
                "estimated_cost": result.usage.total_tokens * 0.00002  # Adjust per model
            }))

        return parse_agent_output(result.final_output)
```

**Step 4: Enhanced Tracing for Sub-agents**

For reporter, charter, and retirement agents, add detailed sub-traces:

```python
# In backend/reporter/agent.py
async def run_reporter_agent(job_id: str, analysis_data: dict) -> str:
    langfuse = setup_langfuse()

    with trace(
        "Generate Portfolio Report",
        metadata={
            "job_id": job_id,
            "report_type": "comprehensive",
            "data_points": len(analysis_data.get("positions", []))
        },
        integration=langfuse
    ):
        # Add performance sub-trace
        with trace("Calculate Performance Metrics"):
            metrics = calculate_performance_metrics(analysis_data)

        # Add recommendation sub-trace
        with trace("Generate Recommendations"):
            model = LitellmModel(model=f"bedrock/{os.getenv('BEDROCK_MODEL_ID')}")

            agent = Agent(
                name="Portfolio Reporter",
                instructions=REPORTER_INSTRUCTIONS,
                model=model,
                tools=[analyze_allocation, calculate_risk_metrics]
            )

            result = await Runner.run(
                agent,
                input=create_report_task(analysis_data, metrics),
                max_turns=10,
                session_id=job_id
            )

        return result.final_output
```

**Step 5: Add LangFuse Credentials to Terraform**

Update `terraform/6_agents/main.tf` to include LangFuse environment variables:

```hcl
# Add variables for LangFuse (optional)
variable "langfuse_public_key" {
  description = "LangFuse public key for observability"
  type        = string
  default     = ""
}

variable "langfuse_secret_key" {
  description = "LangFuse secret key for observability"
  type        = string
  default     = ""
  sensitive   = true
}

variable "langfuse_host" {
  description = "LangFuse host URL"
  type        = string
  default     = "https://cloud.langfuse.com"
}

# Add to each Lambda function
resource "aws_lambda_function" "planner" {
  # ... existing configuration ...

  environment {
    variables = {
      # ... existing variables ...
      LANGFUSE_PUBLIC_KEY = var.langfuse_public_key
      LANGFUSE_SECRET_KEY = var.langfuse_secret_key
      LANGFUSE_HOST       = var.langfuse_host
      ENVIRONMENT         = "production"
      AGENT_VERSION       = "1.0"
    }
  }
}
```

### Setting Up Your LangFuse Account

1. **Create a Free LangFuse Account**
   - Go to https://cloud.langfuse.com
   - Sign up for a free account
   - Create a new project called "Alex Financial Advisor"

2. **Get Your API Credentials**
   - Navigate to Settings → API Keys
   - Create a new API key pair
   - Copy the Public Key and Secret Key

3. **Configure Terraform Variables**
   - Create `terraform/6_agents/terraform.tfvars`:
   ```hcl
   langfuse_public_key = "pk-lf-xxx"
   langfuse_secret_key = "sk-lf-xxx"
   langfuse_host       = "https://cloud.langfuse.com"
   ```

4. **Deploy the Updates**
   ```bash
   cd terraform/6_agents
   terraform apply
   ```

### Using LangFuse Dashboard

Once deployed, the LangFuse dashboard provides:

1. **Traces View**
   - See all agent executions
   - Filter by job_id, user_id, or agent
   - View complete conversation flows
   - Identify slow or failed executions

2. **Token Usage & Costs**
   - Track token consumption per agent
   - Monitor costs across different models
   - Set up usage alerts
   - Optimize expensive operations

3. **Performance Metrics**
   - Agent response times
   - Success/failure rates
   - Token usage trends
   - Model performance comparison

4. **Debug Failed Runs**
   - View exact prompts and responses
   - See error messages and stack traces
   - Replay agent conversations
   - Identify prompt issues

5. **User Analytics**
   - Track unique users
   - Analyze usage patterns
   - Identify power users
   - Monitor user satisfaction

### Advanced LangFuse Features

**Custom Scoring for Quality Monitoring:**
```python
# Add to agent after getting result
if langfuse and result.final_output:
    # Score based on output quality
    output_length = len(result.final_output)
    has_recommendations = "recommend" in result.final_output.lower()

    quality_score = 0.5  # Base score
    if output_length > 1000:
        quality_score += 0.25
    if has_recommendations:
        quality_score += 0.25

    langfuse.score(
        trace_id=trace.id,
        name="output_quality",
        value=quality_score,
        comment=f"Length: {output_length}, Has recommendations: {has_recommendations}"
    )
```

**User Feedback Integration:**
```python
# In API endpoint after user rates analysis
@app.post("/api/feedback")
async def submit_feedback(
    job_id: str,
    rating: int,
    comment: Optional[str] = None,
    user=Depends(clerk_guard)
):
    # Store feedback in database
    db.jobs.add_feedback(job_id, rating, comment)

    # Send to LangFuse for correlation
    if langfuse:
        langfuse.score(
            session_id=job_id,
            name="user_satisfaction",
            value=rating / 5.0,  # Normalize to 0-1
            comment=comment
        )
```

## Conclusion: Your Enterprise-Grade AI System

🎉 **Congratulations!** You've successfully deployed an enterprise-grade agentic AI system!

### What You've Accomplished

You've built a production-ready financial advisory platform that is:

• **Scalable**: Serverless architecture automatically handles load from 1 to 1,000,000+ users
• **Secure**: Multi-layered security with IAM, JWT auth, API throttling, CORS, XSS protection, and secrets management
• **Robust & Monitored**: Comprehensive CloudWatch logging, dashboards, alarms, and SQS dead-letter queues for reliability
• **Guarded**: Input validation, output verification, retry logic, and graceful error handling protect against AI failures
• **Explainable**: AI decisions include rationale, audit trails track all operations, and reasoning is transparent
• **Observable**: Complete LangFuse integration provides traces, token usage, costs, and performance metrics for every AI interaction

### Your Production Deployment Checklist

Before launching to real users:

- [ ] Set up LangFuse account and deploy with credentials
- [ ] Configure CloudWatch dashboards and alarms
- [ ] Set billing alerts in AWS Cost Explorer
- [ ] Run load tests to validate scalability
- [ ] Review IAM permissions (least privilege)
- [ ] Enable AWS WAF for additional protection
- [ ] Document runbooks for common issues
- [ ] Set up on-call rotation for monitoring
- [ ] Create user feedback mechanism
- [ ] Plan for regular security audits

### The Journey from Prototype to Production

You've transformed a simple AI prototype into a robust, enterprise-ready system. This journey mirrors what happens in real organizations as they move from AI experiments to production deployments.

Key lessons learned:
1. **Architecture Matters**: Serverless scales effortlessly
2. **Security is Layered**: No single point of failure
3. **Observability is Critical**: You can't fix what you can't see
4. **AI Needs Guardrails**: Trust but verify
5. **Explainability Builds Trust**: Users need to understand AI decisions

### Next Steps for Continuous Improvement

Your platform is ready for production, but the journey doesn't end here:

1. **A/B Testing**: Test different models and prompts
2. **Fine-tuning**: Create custom models for your domain
3. **Feature Expansion**: Add more sophisticated analysis
4. **Integration**: Connect to real brokerage APIs
5. **Compliance**: Add SOC2, GDPR, or financial regulations as needed

### Final Thoughts

You've built more than just an application - you've created a blueprint for deploying AI agents in production. The patterns, practices, and infrastructure you've implemented here can be adapted for any enterprise AI system.

Welcome to the world of production AI deployment. Your agentic AI system is ready to serve users at scale! 🚀

---

**Thank you for completing the Alex Financial Advisor deployment series!**

For questions, issues, or to share your success stories, please visit our GitHub repository or community forums.

Happy deploying! 🎯