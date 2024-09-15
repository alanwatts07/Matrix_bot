import requests
import asyncio
import aiohttp
import time
import random
import sys
import json
from colorama import init, Fore, Style
import traceback
import os 
import math
# Initialize colorama for colored text
init(autoreset=True)

RUGCHECK_API_BASE_URL = 'https://api.rugcheck.xyz/v1'

# Paths for log and stats files
LOG_FILE_PATH = "snipe_python_found_tokens.json"
STATS_FILE_PATH = "snipe_python_stats.json"
SAFE_TOKENS_FILE_PATH = "safe_tokens.json"  # New file for storing safe tokens
RISK_FILE = "risks.json"
# Initialize statistics
stats = {
    "tokens_scanned": 0,
    "tokens_scanned_lifetime": 0,
    "tokens_detected_as_danger": 0,
    "tokens_detected_as_warn": 0,
    "tokens_detected_as_logged": 0,
    "tokens_skipped_due_to_error": 0,  
    "tokens_pool_liquidity_safe": 0  # New field to track tokens with Safe pool liquidity
}

# Load existing stats from file
def load_stats():
    try:
        with open(STATS_FILE_PATH, 'r') as file:
            loaded_stats = json.load(file)
            # Ensure the 'tokens_pool_liquidity_safe' key exists
            if 'tokens_pool_liquidity_safe' not in loaded_stats:
                loaded_stats['tokens_pool_liquidity_safe'] = 0
            return loaded_stats
    except FileNotFoundError:
        return stats  # Return the default stats dictionary if the file doesn't exist


# Save stats to file
def save_stats():
    with open(STATS_FILE_PATH, 'w') as file:
        json.dump(stats, file, indent=4)

# Append token data to the log file
def log_token(token_data):
    try:
        # Load existing data
        if not os.path.exists(LOG_FILE_PATH):
            tokens = []
        else:
            with open(LOG_FILE_PATH, 'r', encoding='utf-8') as file:
                try:
                    tokens = json.load(file)
                except json.JSONDecodeError:
                    tokens = []

        # Add the new token at the beginning of the list
        tokens.insert(0, token_data)

        # Write the updated list back to the file
        with open(LOG_FILE_PATH, 'w', encoding='utf-8') as file:
            json.dump(tokens, file, ensure_ascii=False, indent=4)

    except Exception as e:
        print_matrix(f"Error writing to log file: {str(e)}", Fore.RED)

# Append safe token data to the safe tokens file# Append safe token data to the safe tokens file
def log_safe_token(token_data):
    try:
        with open(SAFE_TOKENS_FILE_PATH, 'a', encoding='utf-8') as file:
            json.dump(token_data, file, ensure_ascii=False, indent=4)
            file.write(',' + '\n')
    except Exception as e:
        print_matrix(f"Error writing to safe tokens file: {str(e)}", Fore.RED)

# Print telemetry data
def print_telemetry():
    print_matrix("\n---- TELEMETRY DATA ----", Fore.CYAN)
    print_matrix(f"TOKENS SCANNED: {stats['tokens_scanned']}", Fore.YELLOW)
    print_matrix(f"TOKENS SCANNED LIFETIME: {stats['tokens_scanned_lifetime']}", Fore.YELLOW)
    print_matrix(f"TOKENS DETECTED AS DANGER: {stats['tokens_detected_as_danger']}", Fore.RED)
    print_matrix(f"TOKENS DETECTED AS WARN: {stats['tokens_detected_as_warn']}", Fore.MAGENTA)
    print_matrix(f"TOKENS DETECTED AS LOGGED: {stats['tokens_detected_as_logged']}", Fore.GREEN)
    print_matrix(f"TOKENS SKIPPED DUE TO ERROR: {stats['tokens_skipped_due_to_error']}", Fore.RED)
    print_matrix(f"TOKENS POOL LIQUIDITY SAFE: {stats['tokens_pool_liquidity_safe']}", Fore.GREEN)
    print_matrix("---------------------------------------\n", Fore.CYAN)

# List of RugCheck API endpoints to validate
endpoints = [
    '/maintenance',          # Basic check if the API is up
    '/leaderboard',          # Check leaderboard ranking
    '/stats/new_tokens',     # Recently detected tokens
    '/stats/recent',         # Most viewed tokens in past 24 hours
    '/stats/trending',       # Most voted for tokens in past 24 hours
    '/stats/verified'        # Recently verified tokens
]

# Function to print in Matrix-style with adjustable speed
def print_matrix(message, color=Fore.GREEN, speed=0.05):
    for char in message:
        print(f"{color}{char}", end='', flush=True)
        time.sleep(random.uniform(speed * 0.5, speed * 1.5))
    print(Style.RESET_ALL)

def print_name_description_score(data, token_name, mint_address, topHolders):
    total_score = 0
    topholder=topHolders[1]['pct']
    if topholder > 3:
                score_multiplier = 2
                score_input = math.floor(topholder)
                penalty = score_input * score_multiplier
                print_matrix(f'top holder is over {score_input}% adding {penalty} pts', Fore.RED)
                total_score += penalty
    # Ensure data is a list
    if not isinstance(data, list):
        print_matrix(f"Error: Expected data to be a list, got {type(data)} instead", Fore.RED)
        return
    
    for item in data:
        if not isinstance(item, dict):
            print_matrix(f"Error: Expected item to be a dict, got {type(item)} instead", Fore.RED)
            continue

        name = item.get('name', 'Unknown Name')
        description = item.get('description', 'No Description')
        #print(topHolders)
        
        scores = {
            "The top 10 users hold more than 70% token supply": 55,
            "One user holds a large amount of the token supply": 45,
            "Low amount of liquidity in the token pool": 5,
            "The top users hold more than 80% token supply": 65,
            "Only a few users are providing liquidity": 5,
            "More tokens can be minted by the owner": 85,
            "Token metadata can be changed by the owner": 5,
            "The top 10 users hold more than 50% token supply": 30,
            "The owner can change the fees at any time": 25,
            "This token is using a verified tokens symbol": 15,
            "A large amount of LP tokens are unlocked, allowing the owner to remove liquidity at any point.": 85,
            "Tokens can be frozen and prevented from trading": 85
        }

# Look up the score using the description. Default to 0 if the description is not found in the dictionary.
        score = scores.get(description, 1000)
        
        if isinstance(score, (int, float)):
            total_score += score
            
        else:
            print_matrix(f"Invalid score type for token {name}: {score} (type: {type(score)})", Fore.RED)
            continue

        print(f"Name: {name}")
        print(f"Description: {description}")
        print(f"Score: {score}")
        print("-" * 40)  # Separator for readability
    if total_score < 10:
        print_matrix(f'🚀🚀🚀Total RugRisk Score for {token_name}: ' + str(total_score), Fore.LIGHTGREEN_EX)
        log_token({"mint": mint_address, "name": token_name, "score": total_score})
        log_safe_token({"mint": mint_address, "name": token_name, "score": total_score})
    elif total_score < 24:
        print_matrix(f'🚀Total RugRisk Score for {token_name}: ' + str(total_score), Fore.LIGHTGREEN_EX)
        log_token({"mint": mint_address, "name": token_name, "score": total_score})
        stats["tokens_detected_as_logged"] += 1
    elif total_score < 101:
        print_matrix( f'Total RugRisk Score for {token_name}: ' + str(total_score), Fore.LIGHTYELLOW_EX)
    else:
        print_matrix( f'Total RugRisk Score for {token_name}: ' + str(total_score), Fore.LIGHTRED_EX) 

# Function to display a loading screen
def loading_screen(duration=2):
    print(Fore.GREEN + "Initializing", end='', flush=True)
    for _ in range(duration):
        for char in "|/-\\":
            print(Fore.GREEN + char, end='', flush=True)
            time.sleep(0.2)
            print('\b', end='', flush=True)
    print(" Complete")
    print(Style.RESET_ALL)

# Function to pretty print the token metadata
def pretty_print_token(metadata):
    print_matrix(f"Token Mint: {metadata.get('mint', 'N/A')}", Fore.CYAN, speed=0.015)  # 2x faster
    #print (metadata)

    votes = metadata.get('votes', {})
    topHolders= metadata.get('topHolders')
    try: 
        topholder=str(math.floor(topHolders[1]['pct']))
    except:
        topholder=0
    print_matrix(f' the top holder has: {topholder}%', Fore.LIGHTCYAN_EX)
    if votes:
        print_matrix("Votes:", Fore.CYAN, speed=0.015)  # 2x faster
        for key, value in votes.items():
            print_matrix(f"  {key}: {value}", Fore.LIGHTGREEN_EX, speed=0.015)  # 2x faster
    else:
        print_matrix("No votes information available.", Fore.MAGENTA, speed=0.015)  # 2x faster
    
    print_matrix("-" * 66, Fore.LIGHTBLUE_EX, speed=0.015)  # 2x faster

# Function to check API availability
async def check_api(session, url, name):
    try:
        async with session.get(url) as response:
            print_matrix(f"{name} API check: OK, Status: {response.status}")
    except Exception as e:
        print_matrix(f"{name} API check: Failed: {str(e)}")

# Function to fetch token metadata
async def fetch_token_metadata(session, mint):
    url = f'{RUGCHECK_API_BASE_URL}/tokens/{mint}/report'
    try:
        async with session.get(url) as response:
            if response.status == 200 and response.content_type == 'application/json':
                data = await response.json()

                # Update token scan statistics
                stats["tokens_scanned"] += 1
                stats["tokens_scanned_lifetime"] += 1

                # Extract the relevant risks
                token_name = data.get('tokenMeta', {}).get('name', 'Unknown')
                mint_address = data.get('mint', mint)
                risks = data.get('risks', [])
                topHolders = data.get('topHolders', [])
                
                # Append risks to the output file
                with open('risks.json', 'a', encoding='UTF-8') as f:
                    for risk in risks:
                        json_data = {
                            "token_name": token_name,
                            "mint_address": mint_address,
                            "risk": risk
                        }
                        json.dump(json_data, f, ensure_ascii=False, indent=4)
                        f.write(',' + '\n')  # To separate each JSON object in the file


                # Safety check for risks
                if not isinstance(risks, list):
                    print_matrix(f"Error: Expected risks to be a list, got {type(risks)} for token {token_name}", Fore.RED)
                    return
                print_name_description_score(risks, token_name, mint_address, topHolders)

                # Adjust output speed of the token data printing to log console
                print_matrix(f"Token: {token_name} ({mint_address})", Fore.CYAN, speed=0.025)  # 2x faster
                # Process individual risks
                for risk in risks:
                    if not isinstance(risk, dict):
                        print_matrix(f"Error: Expected risk to be a dict, got {type(risk)} in token {mint_address}", Fore.RED)
                        continue

                    name = risk.get('name', 'Unknown Risk')
                    score = risk.get('score', 0)
                    level = risk.get('level', 'Unknown Level')

                    # Check for specific risks
                    if 'Freeze Authority still enabled' in name:
                        print_matrix(f"Freeze authority enabled!!", Fore.LIGHTRED_EX, speed=0.025)
                        

                    if 'Mint Authority still enabled' in name:
                        print_matrix(f"Mint Authoruity Enabled!!", Fore.LIGHTRED_EX, speed=0.025)
                        

                        

                pretty_print_token(data)
            else:
                # Handle non-200 or invalid content-type responses
                stats["tokens_skipped_due_to_error"] += 1
                content = await response.text()
                print_matrix(f'Status: {response.status}, Content: {content}\n', Fore.GREEN, speed=0.015)
    except Exception as e:
        print_matrix(f'Error fetching metadata for {mint}: {str(e)}\n{traceback.format_exc()}', Fore.RED, speed=0.005)
    await asyncio.sleep(3)

# Function to fetch new tokens
async def fetch_new_tokens(session):
    url = f'{RUGCHECK_API_BASE_URL}/stats/new_tokens'
    try:
        async with session.get(url) as response:
            data = await response.json()
            print_matrix(f'Fetched {len(data)} new tokens:', Fore.GREEN, speed=0.025)  # Speed it up Print the number of tokens fetched
            for token in data:
                print_matrix(token['mint'], Fore.LIGHTBLUE_EX, speed=0.005)  # Speed it up
            await asyncio.sleep(3)
            return [token['mint'] for token in data]
    except Exception as e:
        print_matrix(f'Error fetching new tokens: {str(e)}', speed=0.001)  # Default speed
        return []

# Function to validate all endpoints
async def validate_endpoints(session):
    print_matrix('Validating RugCheck API endpoints...', Fore.LIGHTMAGENTA_EX)
    tasks = [check_api(session, f'{RUGCHECK_API_BASE_URL}{endpoint}', endpoint) for endpoint in endpoints]
    await asyncio.gather(*tasks)
    await asyncio.sleep(3)
    print_matrix('RugCheck API validation complete.', Fore.LIGHTMAGENTA_EX)
    print(Style.RESET_ALL)

# Function to validate tokens and inspect metadata











async def validate_tokens(session, mints):
    print_matrix('Validating and inspecting token metadata...', Fore.LIGHTMAGENTA_EX)
    print_matrix('Taking a breath for the API universe here...', Fore.LIGHTMAGENTA_EX)
    print_matrix("--------------------------------------------\n", Fore.CYAN)
    await asyncio.sleep(7)
    for mint in mints:
        await fetch_token_metadata(session, mint)
        # This setting is finikey if 5 seconds  lots of rate errors
        # if 10 seconds not many rate errors at all
        await asyncio.sleep(10)  # Add a 5-second pause between each token metadata check
    print_matrix('Token metadata validation complete.', Fore.LIGHTMAGENTA_EX)
    print(Style.RESET_ALL)

# Main function to manage the tasks
async def main():
    global stats
    stats = load_stats()
    try:
        while True:
            print_matrix("Welcome to RugRiskBot v2.3 - The Matrix Protocol 🚀", Fore.LIGHTGREEN_EX)
            loading_screen(3)
            async with aiohttp.ClientSession() as session:
                await validate_endpoints(session)
                tokens = await fetch_new_tokens(session)
                await validate_tokens(session, tokens)
            print_telemetry()  # Output telemetry data after each cycle
            save_stats()  # Save stats after each cycle
            print_matrix("\nRestarting cycle...\n", Fore.CYAN)
            await asyncio.sleep(5)  # Wait before starting a new cycle
    except KeyboardInterrupt:
        print_matrix("\nProcess interrupted by user. Exiting...", Fore.RED)        
        save_stats()
        sys.exit(0)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_matrix("\nProcess interrupted by user. Exiting...", Fore.RED)
        save_stats()
        sys.exit(0)
