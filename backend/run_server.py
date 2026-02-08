"""Simple server runner that keeps uvicorn alive."""
import uvicorn
import sys
import signal

def handle_signal(sig, frame):
    print(f"\nReceived signal {sig}, shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

if __name__ == "__main__":
    print("=" * 50)
    print("  Starting Bharat Biz-Agent Backend")
    print("=" * 50)
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )
