# Project "Alex"
- This is part of Ed's course "AI in Production"
- Students may be on Windows PC, Mac or Linux; the instructions needs to work on all systems
- This project is called Alex - the Agentic Lifetime Equities Explainer - it's an Agentic AI Platform to be your personal financial planner for your portfolios, deployed on AWS
- The project root is ~/projects/alex
- There is a .env file in the project root; you may not be able to see it for security reasons, but it's there, with OPENAI_API_KEY
- The guides folder contains instructions for each step of the project. These guides are for students, NOT for Ed (the user). For example: if we need to add a Python package, Ed (or you) need to run `uv add package_name`. The students will NOT need to do this, because it will be in pyproject.toml, and in the repo.
- The students might be in any AWS region. BE VERY THOUGHTFUL about this. Some infrastructure must be in us-east-1, but mostly it must be in the student's region.
- ALWAYS be as simple as possible. Always be idiomatic - use simple, popular, common, up-to-date approaches.
- Approach in small steps that can be tested carefully.

## Project organization
backend
- There will be separate projects within this folder for each of the backend deployments
- Each one will have its own uv project
frontend
- A NextJS typescript app will be built eventually
terraform
- Here will be the terraform scripts for the deployment

We have completed Parts 1-4 and we are now working on Part 5.
The full description and to-do list is in the document guides/gameplan.md
And the agent architecture is in guides/agent_architecture.md
