# Railway Deployment Guide

This guide will help you deploy your RAG API to Railway while keeping all your data persistent in the backend.

## 🚀 Quick Start

### Prerequisites
- Railway account (free at [railway.app](https://railway.app))
- OpenAI API key
- Git repository (GitHub, GitLab, or Bitbucket)

### Step 1: Prepare Your Repository

1. **Commit all files to Git:**
   ```bash
   git add .
   git commit -m "Prepare for Railway deployment"
   git push origin main
   ```

2. **Set up environment variables locally:**
   ```bash
   cp railway.env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

### Step 2: Deploy to Railway

1. **Connect to Railway:**
   - Go to [railway.app](https://railway.app)
   - Sign in with your GitHub/GitLab account
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

2. **Configure Environment Variables:**
   In Railway dashboard, go to Variables tab and add:
   ```
   OPENAI_API_KEY=your_actual_openai_api_key_here
   DOCUMENTS_DIR=/app/data/documents
   EMBEDDINGS_DIR=/app/data/embeddings
   ```

3. **Deploy:**
   - Railway will automatically detect the Dockerfile
   - Click "Deploy" and wait for the build to complete
   - Your API will be available at the provided Railway URL

### Step 3: Upload Your Data

**Option A: Using the Upload Script (Recommended)**
```bash
# Install requests if not already installed
pip install requests

# Run the upload script
python scripts/upload_data_to_railway.py https://your-app.railway.app
```

**Option B: Manual Upload via API**
```bash
# Upload a single document
curl -X POST -F "file=@your_document.pdf" https://your-app.railway.app/documents/upload

# Check health
curl https://your-app.railway.app/health
```

## 📁 Data Persistence

### How Data Persists on Railway

✅ **Your data WILL persist** because:
- Railway provides persistent storage for Docker containers
- Your data directories (`/app/data/documents` and `/app/data/embeddings`) are mounted as persistent volumes
- Data survives deployments, restarts, and updates
- No data loss during Railway maintenance

### Data Storage Structure
```
/app/data/
├── documents/          # Your PDF and Excel files
│   ├── *.pdf
│   └── *.xlsx
└── embeddings/         # FAISS indexes and metadata
    ├── *.index
    └── *.json
```

## 🔧 Configuration Details

### Railway Configuration Files

- **`railway.json`**: Railway-specific deployment settings
- **`Procfile`**: Process definition for Railway
- **`dockerfile`**: Multi-stage Docker build optimized for Railway

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `DOCUMENTS_DIR` | Documents storage path | `/app/data/documents` |
| `EMBEDDINGS_DIR` | Embeddings storage path | `/app/data/embeddings` |
| `PORT` | Server port | Set by Railway |

## 🚀 Deployment Process

### Automatic Deployment
1. Push to your main branch
2. Railway automatically builds and deploys
3. Your API is live at the Railway URL

### Manual Deployment
1. Go to Railway dashboard
2. Click "Deploy" button
3. Monitor build logs
4. Access your API when ready

## 📊 Monitoring & Logs

### Health Check
- Endpoint: `GET /health`
- Returns: `{"status": "ok", "version": "0.1.0"}`

### View Logs
- Go to Railway dashboard
- Click on your service
- View "Deployments" tab for logs

### API Documentation
- Swagger UI: `https://your-app.railway.app/docs`
- ReDoc: `https://your-app.railway.app/redoc`

## 🔒 Security Considerations

### Environment Variables
- Never commit API keys to Git
- Use Railway's environment variable system
- Rotate keys regularly

### CORS Configuration
- Current setup allows all origins (`*`)
- For production, restrict to specific domains:
  ```python
  allow_origins=["https://yourdomain.com"]
  ```

## 🛠️ Troubleshooting

### Common Issues

1. **Build Fails**
   - Check Railway build logs
   - Ensure all dependencies are in `pyproject.toml`
   - Verify Dockerfile syntax

2. **Data Not Persisting**
   - Ensure data directories are created in Dockerfile
   - Check file permissions
   - Verify environment variables

3. **API Not Responding**
   - Check health endpoint: `/health`
   - Verify environment variables are set
   - Check Railway service logs

4. **Memory Issues**
   - Railway has memory limits
   - Consider upgrading plan for large documents
   - Monitor memory usage in logs

### Getting Help

- Railway Documentation: [docs.railway.app](https://docs.railway.app)
- Railway Discord: [discord.gg/railway](https://discord.gg/railway)
- Check Railway service logs for detailed error messages

## 💰 Cost Considerations

### Railway Pricing
- **Free Tier**: $5 credit monthly
- **Pro Plan**: Pay-as-you-use
- **Data Storage**: Included in persistent storage

### Optimization Tips
- Use single worker (`--workers 1`) to save memory
- Monitor resource usage
- Consider upgrading if processing large documents

## 🎯 Next Steps

1. **Deploy**: Follow the quick start guide
2. **Test**: Upload documents and test API endpoints
3. **Monitor**: Check logs and performance
4. **Scale**: Upgrade plan if needed
5. **Custom Domain**: Add custom domain in Railway settings

## 📝 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/documents/upload` | Upload document |
| POST | `/documents/text` | Process text directly |
| GET | `/documents/{id}` | Get document info |
| POST | `/qa` | Ask questions using RAG |
| POST | `/chat` | Chat with documents |
| GET | `/onace` | Get ONACE categories |

---

**🎉 Congratulations!** Your RAG API is now deployed on Railway with persistent data storage!
