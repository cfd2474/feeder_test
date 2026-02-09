# TAKNET-PS v2.43.0 - Complete Installation Package

## 🎯 What's in This Package

**Complete TAKNET-PS system with ADSBHub support**

✅ docker-compose.yml with 4 containers (ultrafeeder, fr24, piaware, adsbhub)  
✅ env-template with all feed variables (FR24, PIAWARE, ADSBHUB)  
✅ Web interface with 8 feeder support  
✅ Installer configured for: cfd2474/feeder_test  
✅ Manual fix script included (fix-adsbhub.sh)  

---

## 🚀 Two Installation Options

### Option 1: Push to GitHub + Fresh Install

```bash
# Extract and push
tar -xzf taknet-ps-complete-v2.43.0-github.tar.gz
cd taknet-ps-complete-v2.43.0-github
git init && git add . && git commit -m "v2.43.0"
git remote add origin https://github.com/cfd2474/feeder_test.git
git push -f origin main

# Wait 2-3 minutes, then fresh install
ssh pi@YOUR_PI
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

### Option 2: Manual Fix (FASTEST)

```bash
# Copy fix-adsbhub.sh to your Pi, then run:
sudo bash fix-adsbhub.sh
```

---

## 📦 Included: fix-adsbhub.sh

**This script adds ADSBHub to existing installations in 2 minutes.**

Run it ON your Raspberry Pi to add the adsbhub service directly.

---

## 🔍 Why "no such service: adsbhub" Error?

**Your Pi's docker-compose.yml doesn't have the adsbhub service.**

The installer downloads docker-compose.yml from GitHub. If your GitHub repo still has the old version (without adsbhub), that's what gets installed.

**Solutions:**
1. Push v2.43.0 to GitHub first, then fresh install
2. OR run fix-adsbhub.sh to add it manually

---

## ✅ Complete Package - Version 2.43.0

All version numbers updated throughout all files.

No editing required - ready to deploy!
