# Dockerfile for Daily Todoist Reviewer Lambda
FROM public.ecr.aws/lambda/nodejs:20

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --omit=dev

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Copy lambda handler to root as index.mjs for ES modules
COPY lambda/index.js ./index.mjs

# Ensure all files are readable
RUN chmod -R 755 . && chmod 644 index.mjs package.json

# Set the handler (index.mjs exports handler)
CMD [ "index.handler" ]
