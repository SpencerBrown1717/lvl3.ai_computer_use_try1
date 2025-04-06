# Deploying Computer Control Agent to Google Cloud Platform

This guide explains how to deploy your Computer Control Agent to Google Cloud Platform (GCP) using Docker containers.

## Prerequisites

1. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and configured
2. [Docker](https://docs.docker.com/get-docker/) installed
3. A GCP project with billing enabled
4. Enable required APIs:
   - Cloud Run API
   - Container Registry API

## Step 1: Build and Test the Docker Container Locally

```bash
# Build the Docker image
docker-compose build

# Run the container locally
docker-compose up
```

You can connect to the running container using a VNC client at `localhost:5900`.

## Step 2: Configure GCP Project

```bash
# Set your GCP project ID
export PROJECT_ID=your-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

## Step 3: Push the Docker Image to Google Container Registry

```bash
# Configure Docker to use gcloud as a credential helper
gcloud auth configure-docker

# Tag the Docker image
docker tag computer-agent:latest gcr.io/$PROJECT_ID/computer-agent:latest

# Push the image to Container Registry
docker push gcr.io/$PROJECT_ID/computer-agent:latest
```

## Step 4: Deploy to Cloud Run

Before deploying, update the `cloud-run-config.yaml` file with your actual project ID.

```bash
# Replace YOUR_PROJECT_ID with your actual project ID
sed -i '' "s/YOUR_PROJECT_ID/$PROJECT_ID/g" cloud-run-config.yaml

# Deploy to Cloud Run
gcloud run services replace cloud-run-config.yaml
```

## Step 5: Access Your Deployed Agent

After deployment, you'll need to set up a way to access the VNC server running in the container. There are several options:

1. **Use a VPN or SSH tunnel**: Set up a secure tunnel to access the VNC port
2. **Deploy a VNC web client**: Add a web-based VNC client to your container
3. **Use Cloud IAP**: Configure Identity-Aware Proxy for secure access

## Important Considerations

1. **Security**: The default configuration doesn't include password protection for VNC. For production, add authentication.
2. **Costs**: Running containers on GCP incurs costs based on usage.
3. **Permissions**: The container needs appropriate permissions to interact with other GCP services.
4. **Networking**: Configure firewall rules to control access to your container.

## Remote Control Options

To control your agent remotely, you can:

1. Create a REST API that triggers predefined workflows
2. Set up scheduled jobs using Cloud Scheduler
3. Implement a web interface for real-time control

## Monitoring and Logging

Enable Cloud Monitoring and Logging to track your agent's performance and troubleshoot issues:

```bash
# Enable monitoring
gcloud services enable monitoring.googleapis.com

# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=computer-agent"
```
