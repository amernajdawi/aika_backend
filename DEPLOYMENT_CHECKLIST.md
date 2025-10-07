# 🚀 Railway Deployment Checklist

## ✅ Pre-Deployment Validation
- [x] **Dockerfile** - Properly configured with Python 3.13, data directories, and uvicorn
- [x] **railway.json** - Correctly references Dockerfile and has proper start command
- [x] **Procfile** - Alternative process definition for Railway
- [x] **Application Structure** - All routers and core modules present
- [x] **Data Structure** - 91 PDFs, 3 Excel files, 93 FAISS indexes ready
- [x] **Dependencies** - All required packages in pyproject.toml
- [x] **Environment Template** - railway.env.example created

## 🚂 Railway Deployment Steps

### 1. Commit and Push Code
```bash
git add .
git commit -m "Ready for Railway deployment with data persistence"
git push origin main
```

### 2. Deploy on Railway
1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub/GitLab
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will automatically detect the Dockerfile

### 3. Configure Environment Variables
In Railway dashboard → Variables tab, add:
```
OPENAI_API_KEY=your_actual_openai_api_key_here
DOCUMENTS_DIR=/app/data/documents
EMBEDDINGS_DIR=/app/data/embeddings
```

### 4. Monitor Deployment
- Watch build logs in Railway dashboard
- Check for any errors during build process
- Wait for "Deployed" status

### 5. Test Your API
```bash
# Health check
curl https://your-app.railway.app/health

# Expected response:
# {"status": "ok", "version": "0.1.0"}
```

## 📊 Data Persistence Verification

### Your Data Will Persist Because:
- ✅ **Dockerfile creates data directories** at `/app/data/documents` and `/app/data/embeddings`
- ✅ **Railway provides persistent storage** for Docker containers
- ✅ **Data survives deployments** and restarts
- ✅ **549MB of data** (405MB documents + 144MB embeddings) included in image

### Verify Data After Deployment:
```bash
# Check if documents are accessible
curl https://your-app.railway.app/documents/

# Upload a test document to verify persistence
curl -X POST -F "file=@test.pdf" https://your-app.railway.app/documents/upload
```

## 🔧 Troubleshooting

### Common Issues:
1. **Build Fails**
   - Check Railway build logs
   - Ensure all dependencies are in pyproject.toml
   - Verify Dockerfile syntax

2. **API Not Responding**
   - Check health endpoint: `/health`
   - Verify OPENAI_API_KEY is set
   - Check Railway service logs

3. **Data Not Found**
   - Ensure data directories exist in container
   - Check file permissions
   - Verify environment variables

### Debug Commands:
```bash
# Check Railway logs
# (In Railway dashboard → Deployments → View logs)

# Test API endpoints
curl https://your-app.railway.app/docs  # Swagger UI
curl https://your-app.railway.app/redoc # ReDoc
```

## 📈 Performance Considerations

### Memory Usage:
- **Current setup**: Single worker (`--workers 1`)
- **Memory optimization**: MALLOC settings configured
- **Data size**: 549MB (within Railway limits)

### Scaling Options:
- **Free tier**: $5 credit monthly
- **Pro plan**: Pay-as-you-use for higher limits
- **Custom domain**: Available in Railway settings

## 🎯 Post-Deployment Tasks

### 1. Test All Endpoints:
- [ ] Health check: `GET /health`
- [ ] Document upload: `POST /documents/upload`
- [ ] Document list: `GET /documents/`
- [ ] QA endpoint: `POST /qa`
- [ ] Chat endpoint: `POST /chat`
- [ ] ONACE categories: `GET /onace`

### 2. Monitor Performance:
- [ ] Check response times
- [ ] Monitor memory usage
- [ ] Watch for errors in logs

### 3. Set Up Monitoring:
- [ ] Configure Railway alerts
- [ ] Set up uptime monitoring
- [ ] Monitor API usage

## 🎉 Success Indicators

Your deployment is successful when:
- ✅ Railway shows "Deployed" status
- ✅ Health check returns `{"status": "ok"}`
- ✅ API documentation loads at `/docs`
- ✅ All your documents are accessible
- ✅ QA endpoint responds to queries

## 📞 Support Resources

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Railway Status**: [status.railway.app](https://status.railway.app)

---

**🚀 Ready to deploy! Your RAG API with persistent data storage is configured and validated.**
