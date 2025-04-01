FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir requests

# Copy agent files
COPY agent.py /app/
COPY spoe-config.conf /app/

# Expose the SPOE agent port
EXPOSE 9000

# Run the agent
CMD ["python", "/app/agent.py"]