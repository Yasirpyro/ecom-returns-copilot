# Cloudinary Setup (Photo Storage)

## Why Cloudinary?
Render's free tier has **ephemeral storage** - uploaded files are deleted when the instance restarts. Cloudinary provides:
- ✅ Persistent cloud storage (free tier: 25GB storage, 25GB bandwidth/month)
- ✅ CDN delivery (fast image loading worldwide)
- ✅ No database bloat from storing binary data
- ✅ Free forever plan

## Setup Steps

### 1. Create Cloudinary Account
1. Go to https://cloudinary.com/users/register_free
2. Sign up with your email
3. Verify your email

### 2. Get Your Credentials
1. Login to Cloudinary dashboard
2. You'll see your **Account Details** on the homepage:
   - **Cloud name**: `dxxxxxxxxxxxxx`
   - **API Key**: `123456789012345`
   - **API Secret**: `xxxx-xxxxxxxxxxxxxxxx-xxxxxx`

### 3. Add to Environment Variables

**Local (.env file):**
```bash
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here
```

**Render (Environment Variables):**
1. Go to your Render dashboard
2. Click on your web service
3. Go to **Environment** tab
4. Add three environment variables:
   - `CLOUDINARY_CLOUD_NAME` = your_cloud_name
   - `CLOUDINARY_API_KEY` = your_api_key
   - `CLOUDINARY_API_SECRET` = your_api_secret
5. Click **Save Changes** (Render will auto-redeploy)

### 4. Test
1. Deploy to Render
2. Upload a photo in the customer chat
3. The photo will be stored in Cloudinary under folder: `ecom-returns/{case_id}/`
4. The photo URL will be: `https://res.cloudinary.com/{cloud_name}/image/upload/...`
5. Photos persist across Render restarts ✅

## Troubleshooting

**Error: "Failed to upload photo: 401 Unauthorized"**
- Check your API credentials are correct
- Make sure API Secret doesn't have extra spaces

**Error: "Failed to upload photo: Must supply cloud_name"**
- CLOUDINARY_CLOUD_NAME is missing from environment variables

**Photos still not showing:**
- Check browser console for CORS errors
- Cloudinary URLs should start with `https://res.cloudinary.com/`
- Old database records may have localhost URLs (they won't work - upload new photos)
