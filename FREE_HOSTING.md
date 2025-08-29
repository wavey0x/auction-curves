# Free Hosting Guide 🆓

This guide shows you how to deploy your auction monitoring system at **zero cost** using free hosting services.

## 🎯 Quick Deployment (5 minutes)

**For Demo/Testing:**
```bash
# Deploy mock mode (no database/blockchain needed)
./run.sh mock
npm run build --prefix ui
```
Upload `ui/dist/` to Vercel → **100% free, fully functional demo**

## 💰 Cost Breakdown

| Component | Free Option | Cost | Limits |
|-----------|-------------|------|--------|
| **Frontend** | Vercel/Netlify | $0 | Unlimited for personal |
| **API** | Vercel Functions | $0 | 12 functions, 100GB bandwidth |
| **Database** | Supabase | $0 | 500MB storage, 100MB transfer |
| **Indexer** | Oracle Cloud VPS | $0 | 1GB RAM, 1 CPU forever |

**Total Monthly Cost: $0** 🎉

## 🚀 Production Free Hosting

### Step 1: Database (Supabase - Free)

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Copy connection string: `postgresql://postgres:[password]@[host]:5432/postgres`
4. Run schema:
   ```sql
   -- Copy contents of data/postgres/schema.sql
   -- Paste into Supabase SQL Editor
   ```

### Step 2: Frontend (Vercel - Free)

```bash
# Build production frontend
cd ui
npm run build

# Deploy to Vercel
npx vercel --prod
# Follow prompts, connect to GitHub repo
```

**Result**: Frontend hosted at `https://your-app.vercel.app`

### Step 3: API (Vercel Functions - Free)

Create `api/index.py` (Vercel adapter):
```python
from monitoring.api.app import app
# Vercel serverless adapter
```

Deploy:
```bash
vercel --prod
```

**Result**: API hosted at `https://your-app.vercel.app/api`

### Step 4: Indexer (Oracle Cloud - Free)

**Option A: Oracle Cloud Always Free VPS**
- 1GB RAM, 1 CPU core forever
- Run Rindexer 24/7

**Option B: Home Server/Raspberry Pi**
- Run locally, connects to cloud database
- Perfect for development

**Option C: Periodic Indexing**
- Use Vercel Cron Functions
- Index every 5 minutes instead of real-time

## 🎭 Mock Mode Deployment

**Perfect for demos, portfolios, and testing:**

```bash
./run.sh mock
cd ui && npm run build
```

Upload to Vercel → **Instant demo with realistic data**

**Benefits:**
- No database needed
- No blockchain needed
- No indexer needed
- Works perfectly on free hosting
- Great for showcasing your UI

## 📋 Free Hosting Checklist

### Frontend (Required)
- [x] Build React app: `npm run build`
- [x] Deploy to Vercel: `vercel --prod`
- [x] Set environment variables in Vercel dashboard
- [x] Connect custom domain (optional)

### API (Required for full functionality)
- [x] Create Vercel Functions adapter
- [x] Deploy API endpoints
- [x] Configure database connection
- [x] Test health endpoint

### Database (Required for real data)
- [x] Create Supabase project
- [x] Run schema migration
- [x] Set connection string in Vercel
- [x] Test database connectivity

### Indexer (Required for live data)
- [x] Choose hosting option (Oracle/home/periodic)
- [x] Configure environment variables
- [x] Test blockchain connectivity
- [x] Verify webhook endpoints

## 🔧 Configuration Examples

### Vercel Environment Variables
```bash
# Frontend (.env.production)
VITE_API_URL=https://your-app.vercel.app/api
VITE_APP_MODE=prod

# API (.env)
DATABASE_URL=postgresql://postgres:pass@db.supabase.co:5432/postgres
NETWORKS_ENABLED=ethereum,polygon
```

### Supabase Setup
```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Run your schema
\i schema.sql

-- Verify tables
\dt
```

## 🌐 Alternative Free Options

### Frontend Options
1. **Vercel** ⭐ (Recommended)
   - Automatic deployments from Git
   - CDN, custom domains
   - Perfect for React apps

2. **Netlify**
   - Similar to Vercel
   - Great build system
   - Form handling

3. **GitHub Pages**
   - Static hosting only
   - Good for simple demos

### Database Options
1. **Supabase** ⭐ (Recommended)
   - PostgreSQL with extensions
   - 500MB free storage
   - Great dashboard

2. **Neon**
   - PostgreSQL compatible
   - 3GB free storage
   - Branching feature

3. **PlanetScale**
   - MySQL compatible
   - 1GB free storage
   - Serverless scaling

### API Options
1. **Vercel Functions** ⭐ (Recommended)
   - Python support
   - Automatic scaling
   - Integrates with frontend

2. **Railway**
   - Full application hosting
   - Docker support
   - Database included

3. **Render**
   - Free tier available
   - Background services
   - PostgreSQL addon

## 🚨 Free Tier Limitations

**Be aware of:**
- **Bandwidth limits**: ~100GB/month (usually enough)
- **Function timeout**: 10s for Vercel (optimize queries)
- **Database storage**: 500MB-3GB (optimize data retention)
- **Build minutes**: ~1000/month (efficient CI/CD)

**Optimization tips:**
- Use pagination for large data sets
- Implement data retention policies
- Cache frequently accessed data
- Use mock mode for development

## 🎉 Success Stories

**Your auction system on free hosting can handle:**
- ✅ Thousands of page views per month
- ✅ Real-time auction monitoring
- ✅ Multiple blockchain networks
- ✅ Professional UI/UX
- ✅ Custom domains

**Perfect for:**
- 📊 Portfolio demonstrations
- 🧪 MVP testing and validation
- 📚 Educational projects
- 🚀 Startup prototypes

## 🆘 Troubleshooting

**Common issues:**
1. **Build fails**: Check Node.js version in Vercel settings
2. **API timeout**: Optimize database queries, add connection pooling
3. **Database full**: Implement data retention, upgrade to paid tier
4. **Too many requests**: Add rate limiting, caching

**Getting help:**
- Check service status pages
- Use provider support (Discord, forums)
- Monitor usage dashboards
- Set up alerts for limits

---

**Remember**: Free hosting is perfect for getting started, but as you grow, you can easily migrate to paid tiers or self-hosted solutions while keeping the same codebase! 🚀