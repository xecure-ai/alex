# Alex Architecture Overview

## System Architecture

The Alex platform uses a modern serverless architecture on AWS, combining AI services with scalable infrastructure:

```mermaid
graph TB
    %% External Users
    User[fa:fa-user User]
    
    %% Frontend (future)
    Frontend[fa:fa-globe Frontend<br/>Next.js App<br/>Coming Soon]
    
    %% API Gateway
    APIGW[fa:fa-shield-alt API Gateway<br/>REST API<br/>API Key Auth]
    
    %% Backend Services
    Lambda[fa:fa-bolt Lambda<br/>alex-ingest<br/>Document Processing]
    AppRunner[fa:fa-server App Runner<br/>alex-researcher<br/>AI Agent Service]
    
    %% AI Services
    SageMaker[fa:fa-brain SageMaker<br/>Embedding Model<br/>all-MiniLM-L6-v2]
    OpenAI[fa:fa-robot OpenAI API<br/>GPT-4.1-mini<br/>Research Agent]
    
    %% Data Storage
    OpenSearch[fa:fa-database OpenSearch<br/>Serverless<br/>Vector Database]
    ECR[fa:fa-archive ECR<br/>Docker Registry<br/>Researcher Images]
    
    %% Connections
    User -->|Research Request| AppRunner
    User -->|Direct Ingest| APIGW
    Frontend -.->|Future| APIGW
    Frontend -.->|Future| AppRunner
    
    APIGW -->|Invoke| Lambda
    AppRunner -->|Store Research| APIGW
    AppRunner -->|Generate| OpenAI
    
    Lambda -->|Get Embeddings| SageMaker
    Lambda -->|Store Vectors| OpenSearch
    
    AppRunner -.->|Pull Image| ECR
    
    %% Styling
    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef ai fill:#10B981,stroke:#047857,stroke-width:2px,color:#fff
    classDef storage fill:#3B82F6,stroke:#1E40AF,stroke-width:2px,color:#fff
    classDef future fill:#E5E7EB,stroke:#9CA3AF,stroke-width:2px,color:#6B7280
    
    class APIGW,Lambda,AppRunner,SageMaker,ECR aws
    class OpenAI ai
    class OpenSearch storage
    class Frontend future
```

## Data Flow

### Research Flow (Guide 4)
1. **User** requests investment research through App Runner
2. **App Runner** (Researcher service) uses OpenAI Agents SDK to generate analysis
3. **OpenAI Agent** researches the topic and creates comprehensive investment insights
4. **App Runner** calls the Ingest API to store the research
5. **Lambda** processes the document, generates embeddings via SageMaker
6. **OpenSearch** stores the document with vector embeddings for semantic search

### Direct Ingest Flow (Guide 3)
1. **User** sends documents directly to API Gateway
2. **API Gateway** authenticates with API key and invokes Lambda
3. **Lambda** processes the document and calls SageMaker for embeddings
4. **SageMaker** returns vector representation of the text
5. **Lambda** stores document + vectors in OpenSearch

### Search Flow
1. **User** queries the knowledge base
2. **Lambda** generates embedding for the query via SageMaker
3. **OpenSearch** performs vector similarity search
4. **Results** returned with semantically similar documents

## Component Details

### API Gateway (Guide 3)
- **Type**: REST API with API Key authentication
- **Endpoint**: `/ingest` - Document ingestion
- **Security**: API keys prevent unauthorized access
- **Integration**: Direct Lambda proxy integration

### Lambda Function (Guide 3)
- **Name**: `alex-ingest`
- **Runtime**: Python 3.12
- **Dependencies**: Packaged with `package.py` for cross-platform deployment
- **Functions**:
  - Document validation and processing
  - Embedding generation via SageMaker
  - OpenSearch indexing with retry logic
  - Metadata enrichment

### SageMaker Endpoint (Guide 2)
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Type**: Serverless inference (auto-scaling)
- **Purpose**: Convert text to 384-dimensional vectors
- **Container**: HuggingFace inference container

### OpenSearch Serverless (Guide 3)
- **Type**: Vector search collection
- **Index**: `alex-knowledge`
- **Features**:
  - k-NN vector similarity search
  - Full-text search capabilities
  - Automatic scaling
  - Encryption at rest

### App Runner (Guide 4)
- **Service**: `alex-researcher`
- **Container**: Docker image from ECR
- **Framework**: FastAPI with OpenAI Agents SDK
- **Auto-scaling**: Managed by App Runner
- **Health checks**: `/health` endpoint monitoring

### ECR Repository (Guide 4)
- **Name**: `alex-researcher`
- **Purpose**: Store Docker images for App Runner
- **Build**: Multi-platform support (linux/amd64)

## Security

- **API Keys**: Protect public endpoints from abuse
- **IAM Roles**: Least-privilege access for each service
- **VPC**: OpenSearch runs in isolated network
- **Encryption**: Data encrypted in transit and at rest
- **Secrets**: Managed via environment variables

## Scaling

All components are serverless or auto-scaling:
- **Lambda**: Scales automatically with requests
- **SageMaker**: Serverless endpoint scales to zero
- **OpenSearch**: Serverless auto-scales storage and compute
- **App Runner**: Automatic scaling based on traffic
- **API Gateway**: Fully managed, no scaling concerns

## Cost Optimization

- **Pay-per-use**: Lambda and SageMaker Serverless only charge when used
- **Auto-scaling**: App Runner scales down to minimum during low traffic
- **Serverless**: No idle compute costs for OpenSearch
- **Free Tier**: Many services stay within AWS free tier for development