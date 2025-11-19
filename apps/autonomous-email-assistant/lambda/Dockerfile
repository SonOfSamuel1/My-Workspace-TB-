# Use AWS Lambda Node.js 20 base image
FROM public.ecr.aws/lambda/nodejs:20

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install Gmail MCP server globally
RUN npm install -g @gongrzhe/server-gmail-autoauth-mcp

# Copy Lambda function code
COPY lambda/index.js ${LAMBDA_TASK_ROOT}/
COPY lambda/package*.json ${LAMBDA_TASK_ROOT}/

# Copy lib directory (required by index.js)
COPY lib/ ${LAMBDA_TASK_ROOT}/lib/

# Install Lambda function dependencies (if any)
WORKDIR ${LAMBDA_TASK_ROOT}
RUN npm install --production

# Set the CMD to the Lambda handler
CMD [ "index.handler" ]
