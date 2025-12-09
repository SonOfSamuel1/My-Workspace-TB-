# Use AWS Lambda Node.js 20 base image
FROM public.ecr.aws/lambda/nodejs:20

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install Gmail MCP server globally
RUN npm install -g @gongrzhe/server-gmail-autoauth-mcp

# Copy Lambda function code (paths relative to lambda/ directory)
COPY index.js ${LAMBDA_TASK_ROOT}/
COPY package*.json ${LAMBDA_TASK_ROOT}/

# Copy lib directory from parent (needs to be copied to build context first)
# Note: lib/ will be copied via SAM build process
COPY lib/ ${LAMBDA_TASK_ROOT}/lib/

# Fix permissions for all copied files
RUN chmod -R 755 ${LAMBDA_TASK_ROOT}/

# Install Lambda function dependencies (if any)
WORKDIR ${LAMBDA_TASK_ROOT}
RUN npm install --production

# Set the CMD to the Lambda handler
CMD [ "index.handler" ]
