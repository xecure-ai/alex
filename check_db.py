from backend.database.src import Database

db = Database()
print("Checking instrument prices...")
instruments = db.client.execute("SELECT symbol, current_price FROM instruments ORDER BY symbol")
for inst in instruments:
    price = inst["current_price"] if isinstance(inst, dict) else None
    symbol = inst["symbol"] if isinstance(inst, dict) else str(inst)
    if price:
        print(f"{symbol}: ${price:.2f}")
    else:
        print(f"{symbol}: N/A")

print("\nChecking recent jobs...")
jobs = db.client.execute("SELECT id, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 5")
for job in jobs:
    print(f"Job {job['id']}: {job['status']} - {job['created_at']}")