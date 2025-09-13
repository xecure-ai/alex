"""
FastAPI backend for Alex Financial Advisor
Handles all API routes with Clerk JWT authentication
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import uuid

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import boto3
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
import httpx
from mangum import Mangum
from dotenv import load_dotenv

from src import Database
from src.schemas import (
    UserCreate,
    AccountCreate,
    PositionCreate,
    JobCreate, JobUpdate,
    JobType, JobStatus
)

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Alex Financial Advisor API",
    description="Backend API for AI-powered financial planning",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.getenv("CLOUDFRONT_URL", ""),
        os.getenv("FRONTEND_URL", "")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
db = Database()
security = HTTPBearer()

# SQS client for job queueing
sqs_client = boto3.client('sqs', region_name=os.getenv('DEFAULT_AWS_REGION', 'us-east-1'))
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL', '')

# Clerk configuration
CLERK_JWKS_URL = os.getenv('CLERK_JWKS_URL', '')
CLERK_ISSUER = os.getenv('CLERK_ISSUER', '')

# Cache for JWKS
jwks_cache = None
jwks_cache_time = None

async def get_jwks():
    """Fetch and cache JWKS from Clerk"""
    global jwks_cache, jwks_cache_time

    # Cache for 1 hour
    if jwks_cache and jwks_cache_time and (datetime.now() - jwks_cache_time).seconds < 3600:
        return jwks_cache

    async with httpx.AsyncClient() as client:
        response = await client.get(CLERK_JWKS_URL)
        response.raise_for_status()
        jwks_cache = response.json()
        jwks_cache_time = datetime.now()
        return jwks_cache

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token from Clerk"""
    token = credentials.credentials

    try:
        # Get JWKS
        jwks = await get_jwks()
        logger.info(f"JWKS loaded successfully with {len(jwks.get('keys', []))} keys")

        # Decode token header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        logger.info(f"Token kid: {kid}")

        # Find the matching key
        rsa_key = None
        for key in jwks.get('keys', []):
            if key['kid'] == kid:
                rsa_key = key
                break

        if not rsa_key:
            logger.error(f"No matching key found for kid: {kid}")
            logger.error(f"Available kids: {[k['kid'] for k in jwks.get('keys', [])]}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find matching key"
            )

        # Convert JWK to key
        try:
            # python-jose expects the key in a specific format
            key = jwk.construct(rsa_key)
        except Exception as e:
            logger.error(f"Failed to construct key from JWK: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid key format"
            )

        # Verify and decode token
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            issuer=CLERK_ISSUER,
            options={"verify_aud": False}  # Clerk doesn't always set audience
        )

        logger.info(f"Token verified successfully for user: {payload.get('sub')}")
        return payload

    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        logger.error(f"Token (first 50 chars): {token[:50] if token else 'None'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

# Request/Response models
class UserResponse(BaseModel):
    user: Dict[str, Any]
    created: bool

class UserUpdate(BaseModel):
    """Update user settings"""
    display_name: Optional[str] = None
    years_until_retirement: Optional[int] = None
    target_retirement_income: Optional[float] = None
    asset_class_targets: Optional[Dict[str, float]] = None
    region_targets: Optional[Dict[str, float]] = None

class AccountUpdate(BaseModel):
    """Update account"""
    account_name: Optional[str] = None
    account_purpose: Optional[str] = None
    cash_balance: Optional[float] = None

class PositionUpdate(BaseModel):
    """Update position"""
    quantity: Optional[float] = None

class AnalyzeRequest(BaseModel):
    analysis_type: str = Field(default="portfolio", description="Type of analysis to perform")
    options: Dict[str, Any] = Field(default_factory=dict, description="Analysis options")

class AnalyzeResponse(BaseModel):
    job_id: str
    message: str

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/user", response_model=UserResponse)
async def get_or_create_user(token_data: Dict = Depends(verify_token)):
    """Get user or create if first time"""
    clerk_user_id = token_data.get('sub')

    if not clerk_user_id:
        raise HTTPException(status_code=400, detail="Invalid token: missing user ID")

    try:
        # Check if user exists
        user = db.users.find_by_clerk_id(clerk_user_id)

        if user:
            return UserResponse(user=user, created=False)

        # Create new user with defaults
        display_name = token_data.get('name') or token_data.get('email', '').split('@')[0] or "New User"

        # Create user with basic info
        # Note: create_user returns the clerk_user_id, not an id
        created_clerk_id = db.users.create_user(
            clerk_user_id=clerk_user_id,
            display_name=display_name,
            years_until_retirement=20,
            target_retirement_income=100000
        )

        # Update with allocation targets using the database client directly
        # since the users table uses clerk_user_id as primary key, not id
        update_data = {
            'asset_class_targets': {"equity": 70, "fixed_income": 30},
            'region_targets': {"north_america": 50, "international": 50}
        }
        db.users.db.update(
            'users',
            update_data,
            "clerk_user_id = :clerk_user_id",
            {'clerk_user_id': created_clerk_id}
        )

        # Fetch the created user
        created_user = db.users.find_by_clerk_id(clerk_user_id)
        logger.info(f"Created new user: {clerk_user_id}")

        return UserResponse(user=created_user, created=True)

    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/user")
async def update_user(user_update: UserUpdate, token_data: Dict = Depends(verify_token)):
    """Update user settings"""
    clerk_user_id = token_data.get('sub')

    try:
        # Get user
        user = db.users.find_by_clerk_id(clerk_user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update user
        update_data = user_update.model_dump(exclude_unset=True)
        db.users.update(user['id'], update_data)

        # Return updated user
        updated_user = db.users.find_by_id(user['id'])
        return updated_user

    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/accounts")
async def list_accounts(token_data: Dict = Depends(verify_token)):
    """List user's accounts"""
    clerk_user_id = token_data.get('sub')

    try:
        # Get accounts for user
        accounts = db.accounts.find_by_user(clerk_user_id)
        return accounts

    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/accounts")
async def create_account(account: AccountCreate, token_data: Dict = Depends(verify_token)):
    """Create new account"""
    clerk_user_id = token_data.get('sub')

    try:
        # Verify user exists
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create account
        account_id = db.accounts.create_account(
            clerk_user_id=clerk_user_id,
            account_name=account.account_name,
            account_purpose=account.account_purpose,
            cash_balance=getattr(account, 'cash_balance', Decimal('0'))
        )

        # Return created account
        created_account = db.accounts.find_by_id(account_id)
        return created_account

    except Exception as e:
        logger.error(f"Error creating account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/accounts/{account_id}")
async def update_account(account_id: str, account_update: AccountUpdate, token_data: Dict = Depends(verify_token)):
    """Update account"""
    clerk_user_id = token_data.get('sub')

    try:
        # Verify account belongs to user
        account = db.accounts.find_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Get user to verify ownership
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user or account['user_id'] != user['id']:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Update account
        update_data = account_update.model_dump(exclude_unset=True)
        db.accounts.update(account_id, update_data)

        # Return updated account
        updated_account = db.accounts.find_by_id(account_id)
        return updated_account

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/accounts/{account_id}/positions")
async def list_positions(account_id: str, token_data: Dict = Depends(verify_token)):
    """Get positions for account"""
    clerk_user_id = token_data.get('sub')

    try:
        # Verify account belongs to user
        account = db.accounts.find_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Get user to verify ownership
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user or account['user_id'] != user['id']:
            raise HTTPException(status_code=403, detail="Not authorized")

        positions = db.positions.find_by_account(account_id)
        return positions

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/positions")
async def create_position(position: PositionCreate, token_data: Dict = Depends(verify_token)):
    """Create position"""
    clerk_user_id = token_data.get('sub')

    try:
        # Verify account belongs to user
        account = db.accounts.find_by_id(position.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Get user to verify ownership
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user or account['user_id'] != user['id']:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Add position
        position_id = db.positions.add_position(
            account_id=position.account_id,
            symbol=position.symbol,
            quantity=position.quantity
        )

        # Return created position
        created_position = db.positions.find_by_id(position_id)
        return created_position

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/positions/{position_id}")
async def update_position(position_id: str, position_update: PositionUpdate, token_data: Dict = Depends(verify_token)):
    """Update position"""
    clerk_user_id = token_data.get('sub')

    try:
        # Get position and verify ownership
        position = db.positions.find_by_id(position_id)
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")

        account = db.accounts.find_by_id(position['account_id'])
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Get user to verify ownership
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user or account['user_id'] != user['id']:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Update position
        update_data = position_update.model_dump(exclude_unset=True)
        db.positions.update(position_id, update_data)

        # Return updated position
        updated_position = db.positions.find_by_id(position_id)
        return updated_position

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/positions/{position_id}")
async def delete_position(position_id: str, token_data: Dict = Depends(verify_token)):
    """Delete position"""
    clerk_user_id = token_data.get('sub')

    try:
        # Get position and verify ownership
        position = db.positions.find_by_id(position_id)
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")

        account = db.accounts.find_by_id(position['account_id'])
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Get user to verify ownership
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user or account['user_id'] != user['id']:
            raise HTTPException(status_code=403, detail="Not authorized")

        db.positions.delete(position_id)
        return {"message": "Position deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def trigger_analysis(request: AnalyzeRequest, token_data: Dict = Depends(verify_token)):
    """Trigger portfolio analysis"""
    clerk_user_id = token_data.get('sub')

    try:
        # Get user
        user = db.users.find_by_clerk_id(clerk_user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create job
        job_id = db.jobs.create_job(
            clerk_user_id=clerk_user_id,
            job_type="portfolio_analysis",
            payload=request.model_dump()
        )

        # Get the created job
        job = db.jobs.find_by_id(job_id)

        # Send to SQS
        if SQS_QUEUE_URL:
            message = {
                'job_id': str(job_id),
                'user_id': user['id'],
                'analysis_type': request.analysis_type,
                'options': request.options
            }

            sqs_client.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(message)
            )
            logger.info(f"Sent analysis job to SQS: {job_id}")
        else:
            logger.warning("SQS_QUEUE_URL not configured, job created but not queued")

        return AnalyzeResponse(
            job_id=str(job_id),
            message="Analysis started. Check job status for results."
        )

    except Exception as e:
        logger.error(f"Error triggering analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str, token_data: Dict = Depends(verify_token)):
    """Get job status and results"""
    clerk_user_id = token_data.get('sub')

    try:
        # Get job
        job = db.jobs.find_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Verify job belongs to user
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user or job['user_id'] != user['id']:
            raise HTTPException(status_code=403, detail="Not authorized")

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs")
async def list_jobs(token_data: Dict = Depends(verify_token)):
    """List user's analysis jobs"""
    clerk_user_id = token_data.get('sub')

    try:
        # Get user
        user = db.users.find_by_clerk_id(clerk_user_id)
        if not user:
            return []

        # Get jobs for user
        jobs = db.jobs.find_all()  # We'll need to filter by user_id
        user_jobs = [job for job in jobs if job.get('user_id') == user['id']]
        return user_jobs

    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Lambda handler
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)