# Use AWS Lambda Node.js 20 base image
FROM public.ecr.aws/lambda/nodejs:20

# Install system dependencies
RUN yum update -y && \
    yum install -y \
    curl \
    wget \
    git \
    && yum clean all

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install Gmail MCP server globally
RUN npm install -g @gongrzhe/server-gmail-autoauth-mcp

# Copy Lambda function code
COPY index.js ${LAMBDA_TASK_ROOT}/
COPY package*.json ${LAMBDA_TASK_ROOT}/

# Install Lambda function dependencies (if any)
WORKDIR ${LAMBDA_TASK_ROOT}
RUN npm install --production

# Set the CMD to the Lambda handler
CMD [ "index.handler" ]
