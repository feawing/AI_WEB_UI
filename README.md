# Using Google ADK and Google A2A protocol to get a Sofime chatbot access to Relo informations

This document explains how to set up and use it

## Setup Instructions 

### Google Studio Credentials

#### Préparation
1. Installer Google Cloud SDK
   Sous windows: sur le site de google : https://cloud.google.com/sdk/docs/install
   Sous Ubuntu : sudo apt-get install google-cloud-sdk
2. Lancer la commande pour génrter le fichier de credentials:
   gcloud auth application-default login
   Attention: relié à un compte google (actuellement maire@reflexe.fr)
   --> le fichier doit etre dans %APPDATA%\gcloud\application_default_credentials.json

#### Deploiement sur une VM en ligne: Création d'un compte de service 
1. Créer le compte de service
--> Console web du projet googlecloud
----> Section IAM et Administration
----> Comptes de service
----> Créer un nouveau compte genre 'vm49-sofime-dev'
----> Attribuer le rôle Utilisateur de Vertex AI
2.Générer une clé pour le compte
--> Toujours dans la console googlecloud / comptes de service
--> Aller dans les détails du compte de service
--> Onglet clés
--> Ajouter une clé
--> Créer une nouvelle clé au format json
----> LE fichier généré est téléchargé. 
3. Placer cette clé json sur la VM 
--> Copier le fichier clé du compte de service
----> Par exemple dans /etc/gcloud/service-acount-key.json
----> Régler la variable d'environnement GOOGLE_APPLICATION_CREDENTIALS


### 1. Install Dependencies

First, create two virtual environments:
```bash
# Create a virtual environment
python -m venv .venv
python -m venv .venvstatus
```

### 2. Activate the virtual environment:
On Windows:
```powershell
# Activate virtual environment on Windows
.venv\Scripts\activate
```
On macOS/Linux:
```bash
# Activate virtual environment on macOS/Linux
source .venv/bin/activate
```
### 3. install all required Python packages using pip:
```bash
# Install all dependencies
pip install -r requirements.txt
```

### 4. activate .venvstatus and install all required Python package using pip 
Each virtual environment is independant

### 5. Set up the .env file (most natably set up Gemini api key) in the project root dir

Note: creation of API keys is at [Google AI Studio](https://aistudio.google.com/) 
[API Keys section](https://aistudio.google.com/app/apikeys)
Note : A2A procotol is a young Google specifications, Gemini models are more likely to handle it correctly (most notably on client side)
Note bis: As of today 04/07/2025 Gemini 2.5 Pro Experimental is supposed to be the best model available. It's also a LOT more expensive than lighter or older gemini models. (see models description and princing at the bottom of this)


## Execution

First Server (Status) then Client (host)
In two separate shells (to avoid ressource access conflict)

### (Server) Activate virtual Environment
On windows powershell
   .venvstatus/Scripts/activate
On linux shell
   source .venvstatus/Scripts/activate

### (server) select server directory
cd app/status_agent_adk

### (server) launch service
uv run --active ./__main__.py --root-path /aisofimestatus

### (client) activate virtual enviroment
On windows powershell
   .venv/Scripts/activate
On linux shell
   source ./.venv/Scripts/activate

### (client) select client directory
cd app

### (client) launch service
uv run --active ./__main__.py



# API Usage

Application will consume Gemini credit on specified  Google account. 
Can be tracked on google ai studio webpage.

## Model Capabilities

| Model | Description | Input Types | Best For |
|-------|-------------|-------------|----------|
| gemini-2.5-pro | Most powerful thinking model with maximum response accuracy | Audio, images, video, text | Complex coding, reasoning, multimodal understanding |
| gemini-2.5-flash | Best price-performance balance | Audio, images, video, text | Low latency, high volume tasks that require thinking |
| gemini-2.0-flash | Newest multimodal model with improved capabilities | Audio, images, video, text | Low latency, enhanced performance, agentic experiences |
| gemini-2.0-flash-lite | Optimized for efficiency and speed | Audio, images, video, text | Cost efficiency and low latency |
| gemini-1.5-flash | Versatile performance across diverse tasks | Audio, images, video, text | Fast and versatile performance |
| gemini-1.5-flash-8b | Smaller, faster model | Audio, images, video, text | High volume and lower intelligence tasks |
| gemini-1.5-pro | Powerful reasoning capabilities | Audio, images, video, text | Complex reasoning tasks requiring more intelligence |

## Pricing

| Model | Input Price | Output Price |
|-------|-------------|-------------|
| gemini-2.5-pro | $10.00 / 1M tokens | $30.00 / 1M tokens |
| gemini-2.5-flash | $3.50 / 1M tokens | $10.50 / 1M tokens |
| gemini-2.0-flash | $3.50 / 1M tokens | $10.50 / 1M tokens |
| gemini-2.0-flash-lite | $0.70 / 1M tokens | $2.10 / 1M tokens |
| gemini-1.5-flash | $2.50 / 1M tokens | $7.50 / 1M tokens |
| gemini-1.5-flash-8b | $0.35 / 1M tokens | $1.05 / 1M tokens |
| gemini-1.5-pro | $7.00 / 1M tokens | $21.00 / 1M tokens |

## Token Information

- A token is approximately 4 characters
- 100 tokens are roughly 60-80 English words
- Pricing is calculated based on both input tokens (prompts sent to the model) and output tokens (responses generated by the model)