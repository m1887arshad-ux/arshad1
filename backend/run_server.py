import uvicorn

if __name__ == "__main__":
    print("=" * 50)
    print("Starting Bharat Biz-Agent Backend")
    print("=" * 50)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
