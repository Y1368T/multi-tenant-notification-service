from fastapi import FastAPI

app = FastAPI(
    title="Notification Service",
    description="Service for sending notifications via email and SMS",
    version="1.0.0"
)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the Notification Service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("notification_service.main:app", host="0.0.0.0", port=8000)