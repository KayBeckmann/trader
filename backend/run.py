import sys
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py [data-fetcher|trainer|knn-worker|trader|api-server]")
        sys.exit(1)

    service = sys.argv[1]
    
    commands = {
        "data-fetcher": ["python", "-u", "data_fetcher.py"],
        "trainer": ["python", "-u", "trainer.py"],
        "knn-worker": ["python", "-u", "knn_worker.py"],
        "trader": ["python", "-u", "trader.py"],
        "api-server": ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        "remove-stocks-worker": ["python", "-u", "remove_stocks_worker.py"]
    }

    command = commands.get(service)

    if command:
        print(f"Starting service: {service}")
        subprocess.run(command)
    else:
        print(f"Unknown service: {service}")
        sys.exit(1)

if __name__ == "__main__":
    main()
