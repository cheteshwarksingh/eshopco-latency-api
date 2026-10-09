# eShopCo latency metrics API

## Deploy
1. Upload this folder to a GitHub repository.
2. In Vercel, choose **Add New → Project**, import the repository, and deploy.
3. The POST endpoint is `https://YOUR-VERCEL-DOMAIN.vercel.app/` (the API is mounted at the root by this project setup). If your deployment exposes the function under `/api`, use `https://YOUR-VERCEL-DOMAIN.vercel.app/api`.

## Test
POST JSON:
```json
{"regions":["emea","apac"],"threshold_ms":165}
```
CORS allows any origin and POST/OPTIONS requests.
