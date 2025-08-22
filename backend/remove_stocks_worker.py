import time
import os

def remove_stocks():
    """Removes stocks listed in keineDaten.md from stocks.txt."""
    try:
        keine_daten_path = '/app/keineDaten.md'
        stocks_path = '/app/stocks.txt'

        if not os.path.exists(keine_daten_path):
            print(f"File not found: {keine_daten_path}")
            return

        if not os.path.exists(stocks_path):
            print(f"File not found: {stocks_path}")
            return

        with open(keine_daten_path, 'r') as f:
            stocks_to_remove = [line.strip() for line in f.readlines() if not line.startswith('#') and line.strip()]

        if not stocks_to_remove:
            print("No stocks to remove.")
            return

        with open(stocks_path, 'r') as f:
            stocks = [line.strip() for line in f.readlines()]

        original_stock_count = len(stocks)
        stocks = [stock for stock in stocks if stock not in stocks_to_remove]
        new_stock_count = len(stocks)

        with open(stocks_path, 'w') as f:
            for stock in stocks:
                f.write(f"{stock}\n")

        print(f"Removed {original_stock_count - new_stock_count} stocks. {new_stock_count} stocks remaining.")

    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    """Main loop for the remove_stocks_worker."""
    print("Starting remove_stocks_worker service...")
    while True:
        print("Running daily stock removal...")
        remove_stocks()
        # Sleep for 24 hours
        time.sleep(60 * 60 * 24)

if __name__ == "__main__":
    main()
