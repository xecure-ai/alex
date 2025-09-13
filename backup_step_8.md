
## Part 8: Observability, Monitoring & Security (NOT STARTED)

### Objective
Implement comprehensive observability with LangFuse, monitoring with CloudWatch, and security best practices.

### Steps

1. **Set Up LangFuse**
   - Deploy LangFuse (Docker on ECS or use cloud version)
   - Configure API keys
   - Set up projects for each agent
   - ✅ **Test**: LangFuse UI accessible, API works

2. **Instrument All Agents**
   - Add LangFuse to OpenAI Agents SDK config
   - Trace every agent call
   - Track tool usage
   - Log prompts and completions
   - Track costs per user
   - ✅ **Test**: Traces appear in LangFuse with full detail

3. **Create CloudWatch Dashboards**
   - Agent invocation metrics
   - Database performance
   - API Gateway metrics
   - Cost tracking
   - Error rates
   - ✅ **Test**: All metrics flowing, alerts working

4. **Implement Security Hardening**
   - API rate limiting (API Gateway)
   - Secrets rotation for Aurora credentials
   - WAF rules for CloudFront
   - Least privilege IAM
   - Data API access controls
   - ✅ **Test**: Security scan with OWASP ZAP

5. **Set Up Cost Monitoring**
   - Budget alerts
   - Per-user cost tracking
   - Bedrock usage monitoring
   - Database cost analysis
   - ✅ **Test**: Cost allocation tags working

### Observability Metrics
- Agent execution time
- Tool call frequency
- Token usage per agent
- Error rates by agent
- User session tracking
- Database query performance

### Security Checklist
- [ ] All secrets in Secrets Manager
- [ ] Data API IAM authentication configured
- [ ] API rate limiting enabled
- [ ] WAF rules active
- [ ] IAM roles follow least privilege
- [ ] Database encrypted at rest
- [ ] S3 buckets private
- [ ] CloudTrail enabled

### Deliverables
- Full observability in LangFuse
- CloudWatch dashboards
- Security hardening complete
- Cost tracking operational

### Acceptance Criteria for Part 8

#### LangFuse Integration for Rich Observability
- [ ] LangFuse accessible and configured
- [ ] All agent Lambda functions send detailed traces
- [ ] Orchestrator creates parent trace with:
  - Job metadata (user, portfolio size, job_id)
  - Agent coordination timeline
  - Decision points ("needs tagging", "retirement analysis required")
- [ ] Each agent creates child trace with:
  - Agent persona/role description
  - Reasoning steps (chain of thought)
  - Input/output tokens with cost
  - Execution time and status
  - Custom metadata (e.g., "instruments_tagged": 5)
- [ ] Visual trace hierarchy shows:
  ```
  📊 Portfolio Analysis Job #123
  ├── 🎯 Financial Planner (Orchestrator)
  │   ├── Decision: Missing data for ARKK, SOFI
  │   └── Routing to: InstrumentTagger
  ├── 🏷️ InstrumentTagger 
  │   ├── Tagged: ARKK → Tech ETF (100% equity)
  │   └── Tagged: SOFI → Fintech Stock (100% equity)
  ├── 📝 Report Writer (Parallel)
  │   └── Generated: 2,500 word analysis
  ├── 📊 Chart Maker (Parallel)
  │   └── Created: 3 visualizations
  └── 🎯 Retirement Specialist (Parallel)
      └── Projection: 85% success rate
  ```
- [ ] Traces linked by job_id for correlation
- [ ] Cost breakdown per agent and total
- [ ] Success/failure status clearly visible

#### CloudWatch Monitoring
- [ ] Custom dashboard created with:
  - Lambda invocation counts
  - Lambda error rates
  - API Gateway request counts
  - SQS queue depth
  - Aurora Data API latency
- [ ] Alarms configured for:
  - Lambda errors > 5% 
  - SQS DLQ messages > 0
  - API Gateway 5xx errors
  - Database connection failures
- [ ] Logs properly structured with JSON

#### Security Hardening
- [ ] API Gateway rate limiting enabled (e.g., 100 requests/minute per IP)
- [ ] WAF rules active on CloudFront:
  - SQL injection protection
  - XSS protection
  - Rate limiting
- [ ] All Lambda environment variables use Secrets Manager
- [ ] Database credentials rotated successfully
- [ ] IAM roles follow least privilege principle
- [ ] S3 buckets have versioning enabled
- [ ] CloudTrail logging enabled for audit

#### Cost Controls
- [ ] AWS Budget alert at $50/month
- [ ] Cost allocation tags on all resources:
  - Project: alex
  - Environment: production
  - Owner: [your-name]
- [ ] Per-user cost tracking via LangFuse
- [ ] Aurora auto-pause configured (pause after 5 minutes idle)

#### Performance Validation
- [ ] Lambda cold starts < 2 seconds
- [ ] API response times < 500ms (excluding analysis jobs)
- [ ] Analysis completion < 3 minutes
- [ ] Frontend loads < 2 seconds on 4G connection
- [ ] Database queries < 100ms

#### Security Testing
- [ ] OWASP ZAP scan shows no high-risk vulnerabilities
- [ ] Attempt SQL injection - properly blocked
- [ ] Attempt XSS - properly sanitized
- [ ] Try accessing API without token - returns 401
- [ ] Try accessing another user's data - returns 403

## Lambda Deployment Technique for Binary Compatibility

### The Architecture Issue
Lambda runs on Amazon Linux 2 (x86_64 architecture). When packaging Python dependencies on macOS (ARM64) or Windows, binary packages like `pydantic_core` are compiled for the wrong architecture, causing runtime failures with errors like:
- `ImportError: cannot import name 'ValidationError' from 'pydantic_core'`
- Binary incompatibility errors for packages with C extensions

### Solution: Docker-Based Packaging
Use Docker with the official AWS Lambda Python runtime image to compile dependencies for the correct architecture. This ensures all binary packages are compatible with Lambda's runtime environment.
