import requests
import random
import time
import json
import os
from tqdm import tqdm
from colorama import Fore, init
from prettytable import PrettyTable

init(autoreset=True)

CLAIM_URL = "https://testnet.humanity.org/api/rewards/daily/claim"
BALANCE_URL = "https://testnet.humanity.org/api/user/balance"
TOKEN_FILE = "tokens.txt"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

def get_random_ua():
    return random.choice(USER_AGENTS)

def countdown_timer(seconds):
    try:
        for remaining in range(seconds, 0, -1):
            hrs, rem = divmod(remaining, 3600)
            mins, secs = divmod(rem, 60)
            timer_display = f"{Fore.YELLOW}⏳ Menunggu {hrs:02}:{mins:02}:{secs:02} untuk siklus berikutnya..."
            print(timer_display, end="\r")
            time.sleep(1)
        print(" " * 60, end="\r")  # Bersihkan baris
    except KeyboardInterrupt:
        print(Fore.RED + "\n⏹ Timer dibatalkan oleh pengguna.")
        exit()

def get_balance(headers):
    try:
        response = requests.get(
            BALANCE_URL,
            headers=headers,
            timeout=15,
            allow_redirects=False
        )
        with open("balance_debug.log", "a") as f:
            f.write(f"Timestamp: {time.ctime()}\n")
            f.write(f"Status Code: {response.status_code}\n")
            f.write(f"Response Body: {response.text}\n\n")
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP Error {response.status_code}",
                "raw": response.text
            }
        try:
            data = response.json()
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid JSON response",
                "raw": response.text
            }
        balance = None
        possible_paths = [
            ['balance'],
            ['data', 'balance'],
            ['result', 'balance'],
            ['account', 'total'],
            ['wallet', 'total'],
            ['data', 'wallet', 'balance'],
            ['response', 'balances', 0, 'amount']
        ]
        for path in possible_paths:
            try:
                current = data
                for key in path:
                    if isinstance(current, list) and isinstance(key, int):
                        current = current[key]
                    else:
                        current = current.get(str(key))
                if current is not None:
                    balance = current
                    break
            except (KeyError, IndexError, TypeError):
                continue
        if balance is None:
            return {
                "success": False,
                "error": "Format balance tidak dikenali",
                "raw": json.dumps(data, indent=2)
            }
        return {
            "success": True,
            "balance": balance,
            "raw": data
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Koneksi gagal"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}

def process_token(token, progress_bar):
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "User-Agent": get_random_ua(),
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br"
    }
    masked_token = f"{token[:12]}...{token[-6:]}" if len(token) > 18 else token
    result = {
        "token": masked_token,
        "claim_status": None,
        "balance_info": None,
        "error": None
    }
    try:
        claim_response = requests.post(
            CLAIM_URL,
            headers=headers,
            json={},
            timeout=15
        )
        result["claim_status"] = claim_response.status_code
        time.sleep(random.uniform(1, 3))
        balance_result = get_balance(headers)
        result["balance_info"] = balance_result
    except Exception as e:
        result["error"] = str(e)
    progress_bar.update(1)
    return result

def format_result(result):
    if result["claim_status"] == 200:
        claim_status = f"{Fore.GREEN}✅ Berhasil"
    elif result["claim_status"]:
        claim_status = f"{Fore.RED}❌ Gagal ({result['claim_status']})"
    else:
        claim_status = f"{Fore.YELLOW}⏳ Tidak diketahui"
    if result["balance_info"]:
        if result["balance_info"]["success"]:
            balance = f"{Fore.CYAN}{result['balance_info']['balance']}"
        else:
            balance = f"{Fore.RED}{result['balance_info']['error']}"
    else:
        balance = f"{Fore.YELLOW}N/A"
    error = result["error"] or "-"
    return [result["token"], claim_status, balance, error]

def main_loop():
    os.system("cls" if os.name == "nt" else "clear")
    print(Fore.CYAN + "\n" + "="*50)
    print(Fore.YELLOW + " HUMANITY CLAIMER ".center(50, "⚡"))
    print(Fore.CYAN + "="*50 + "\n")
    try:
        with open(TOKEN_FILE, "r") as f:
            tokens = [t.strip() for t in f.readlines() if t.strip()]
        if not tokens:
            print(Fore.RED + "❌ Error: Tidak ada token yang ditemukan di file!")
            return
        print(Fore.WHITE + f"🔍 Ditemukan {len(tokens)} token\n")
    except Exception as e:
        print(Fore.RED + f"❌ Gagal membaca file token: {str(e)}")
        return
    results = []
    with tqdm(total=len(tokens), desc=Fore.BLUE + "Memproses Token", 
             bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as pbar:
        for token in tokens:
            results.append(process_token(token, pbar))
            time.sleep(0.5)
    table = PrettyTable()
    table.field_names = [
        Fore.CYAN + "Token",
        Fore.CYAN + "Claim Status",
        Fore.CYAN + "Balance",
        Fore.CYAN + "Error"
    ]
    table.align = "l"
    for res in results:
        table.add_row(format_result(res))
    print(Fore.GREEN + "\n" + "📊 HASIL AKHIR ".center(50, "="))
    print(table)
    with open("claim_log.txt", "a") as f:
        f.write(f"Claim Log - {time.ctime()}\n\n")
        for res in results:
            f.write(f"Token: {res['token']}\n")
            f.write(f"Claim Status: {res['claim_status']}\n")
            if res["balance_info"]:
                f.write(f"Balance Result: {json.dumps(res['balance_info'], indent=2)}\n")
            f.write(f"Error: {res['error']}\n")
            f.write("-"*50 + "\n")
    print(Fore.YELLOW + "\nLog detail disimpan di: claim_log.txt")
    print(Fore.MAGENTA + "="*50)

def main():
    try:
        while True:
            main_loop()
            print(Fore.GREEN + f"\n🔁 Menunggu 6 jam sebelum siklus berikutnya...\n")
            countdown_timer(6 * 60 * 60)  
    except KeyboardInterrupt:
        print(Fore.RED + "\n⏹ Dihentikan oleh pengguna!")

if __name__ == "__main__":
    main()
