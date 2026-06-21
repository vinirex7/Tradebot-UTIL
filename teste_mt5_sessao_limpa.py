import MetaTrader5 as mt5

MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"

ok = mt5.initialize(path=MT5_PATH)

print("initialize:", ok)
print("last_error:", mt5.last_error())

if not ok:
    raise SystemExit

account = mt5.account_info()
terminal = mt5.terminal_info()

print("\nACCOUNT:")
print(account)

print("\nTERMINAL:")
print(terminal)

print("\nSÍMBOLOS UTIL:")
for ticker in ["SBSP3", "EQTL3", "CPLE3", "CMIG4", "ENGI11", "AURE3"]:
    info = mt5.symbol_info(ticker)
    print(ticker, "OK" if info else "NÃO ENCONTRADO")

mt5.shutdown()