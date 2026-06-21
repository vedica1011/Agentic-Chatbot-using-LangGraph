# Multi-Tenant Gemini Chatbot: Deployment & Architecture Guide

This document serves as a complete, step-by-step guide to building and deploying the Multi-Tenant Gemini Chatbot to Google Cloud Platform (GCP) using Google Kubernetes Engine (GKE) and GitHub Actions.

---

## 1. Architecture & Services Explained
### Why separate Frontend and Backend?
* **Backend (FastAPI)**: Handles the database, validates Tenant IDs, and communicates securely with the Gemini API. We keep it hidden from the public internet for security.
* **Frontend (Streamlit)**: Provides the user interface. It communicates exclusively with the Backend.

### Google Cloud Services We Used
* **Google Kubernetes Engine (GKE)**: The orchestration system that runs our application inside Docker containers. It ensures the app stays online and can scale.
* **Artifact Registry (GAR)**: A private cloud storage bucket where our built Docker images are stored before Kubernetes pulls them.
* **IAM Service Account**: A "robot account" that we gave to GitHub Actions so it has permission to push code into our Google Cloud project without needing a human to log in.

---

## 2. Understanding the YAML Files

### `k8s/backend-deployment.yaml` & `k8s/frontend-deployment.yaml`
These files are instructions for Kubernetes on how to run our app.
* **`replicas: 1`**: Tells Kubernetes to run exactly 1 copy of the container. We initially tried 2, but scaled it down to 1 to avoid hitting GCP Free-Tier CPU/Memory quota limits ("Insufficient Memory").
* **`image: PLACEHOLDER`**: GitHub Actions automatically replaces this word with the actual Docker image link right before deploying.
* **`ClusterIP` (Backend)**: A Kubernetes Service type that makes the backend *internal only*. Only other apps inside the cluster (like the frontend) can talk to it.
* **`LoadBalancer` (Frontend)**: A Kubernetes Service type that asks Google Cloud to assign a public, external IP address so anyone on the internet can visit the site.
* **`secretKeyRef` (Backend)**: Injects highly sensitive data (like the Gemini API Key) safely from a Kubernetes Secret into the pod as an environment variable.

### `.github/workflows/deploy-gke.yaml`
This file automates the deployment pipeline every time you `git push`.
* **`google-github-actions/auth@v2`**: Logs into Google Cloud using the JSON key we saved in GitHub Secrets.
* **`docker build` & `docker push`**: Packages our backend and frontend code into containers and uploads them to Artifact Registry.
* **`sed -i`**: A Linux command that searches the Kubernetes YAML files for our `PLACEHOLDER` text and overwrites it with the newly built Docker image tag.
* **`kubectl apply`**: Sends the updated YAML files to GKE to spin up the new code.

---

## 3. Step-by-Step Deployment History
*These are the exact commands we successfully used to troubleshoot and deploy the application from start to finish.*

### Step 1: Gather GCP Credentials
We used the Google Cloud CLI to find the exact names of our resources:
```bash
# Find Artifact Registry Name
gcloud artifacts repositories list --project=YOUR_PROJECT_ID --location=us-central1

# Find Service Account Email
gcloud iam service-accounts list --project=YOUR_PROJECT_ID

# Find GKE Cluster Name and Region
gcloud container clusters list --project=YOUR_PROJECT_ID
```

### Step 2: Grant Permissions to the Service Account
We needed to ensure the Service Account had the authority to push Docker images, update Kubernetes, and generate access tokens.
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member="serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL" --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member="serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL" --role="roles/container.developer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member="serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL" --role="roles/iam.serviceAccountTokenCreator"
```

### Step 3: Configure GitHub Actions Auth
Instead of using complex Workload Identity Federation, we opted for a secure, straightforward JSON key.
```bash
# Generate and download the JSON key
gcloud iam service-accounts keys create gcp-key.json --iam-account=YOUR_SERVICE_ACCOUNT_EMAIL
```
*We then copied the contents of `gcp-key.json` into GitHub > Settings > Secrets > `GCP_CREDENTIALS`.*

### Step 4: Fix Kubernetes CLI Access
Modern `gcloud` versions require an authentication plugin to communicate with GKE clusters.
```bash
# Install the missing plugin
gcloud components install gke-gcloud-auth-plugin

# Connect your terminal to the remote GKE cluster
gcloud container clusters get-credentials agentic-chatbot-cluster --region us-central1 --project YOUR_PROJECT_ID
```

### Step 5: Create the Kubernetes Secrets
If the backend pod boots up and cannot find the API Key or Database URL, it crashes immediately (`Exceeded progress deadline`). We fixed this by manually injecting the secret into the cluster:
```bash
kubectl create secret generic backend-secrets \
  --from-literal=database-url="sqlite:///./chatbot.db" \
  --from-literal=google-api-key="YOUR_REAL_API_KEY_HERE"
```

*(After this step, the GitHub Action deployment succeeded!)*

### Step 6: Access the Application
To get the public IP address generated by the `LoadBalancer`:
```bash
kubectl get service frontend-service
```
*(You navigate to the `EXTERNAL-IP` in your web browser to see the UI).*

### Step 7: Register the First Tenant
Because the app is multi-tenant and securely blocks unauthorized access, you must create a Tenant ID before chatting.
```bash
# Open a secure tunnel from your local machine directly to the private backend pod
kubectl port-forward svc/backend-service 8000:8000
```
*With the tunnel open, you navigate to `http://localhost:8000/docs` in your browser, use the `POST /admin/tenants` endpoint, and create a tenant (e.g., `tenant-001`). Then, you can enter `tenant-001` into the live Streamlit UI and begin chatting!*
