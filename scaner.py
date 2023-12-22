import os
import binascii
import hashlib
import base58
import ecdsa
import asyncio
import aiohttp
from colorama import Fore, Style, init

init(autoreset=True)

def generate_private_key():
    # Générer 32 octets aléatoires (256 bits) pour la clé privée
    private_key_bytes = os.urandom(32)
    
    # Convertir les octets en une représentation hexadécimale
    private_key_hex = binascii.hexlify(private_key_bytes).decode('utf-8')
    
    return private_key_hex

def generate_next_private_keys(first_private_key, num_keys):
    private_keys = [first_private_key]
    
    for _ in range(num_keys - 1):
        # Convertir la clé privée actuelle en octets
        current_private_key_bytes = binascii.unhexlify(private_keys[-1])
        
        # Ajouter 1 à la valeur entière représentée par les octets
        next_private_key_bytes = int.from_bytes(current_private_key_bytes, 'big') + 1
        
        # Convertir la nouvelle valeur en octets
        next_private_key_bytes = next_private_key_bytes.to_bytes(32, 'big')
        
        # Convertir les octets en une représentation hexadécimale
        next_private_key_hex = binascii.hexlify(next_private_key_bytes).decode('utf-8')
        
        private_keys.append(next_private_key_hex)
    
    return private_keys

def private_keys_to_wifs(private_keys):
    wifs = []
    for private_key_hex in private_keys:
        extended_key = "80" + private_key_hex
        first_sha256 = hashlib.sha256(binascii.unhexlify(extended_key)).hexdigest()
        second_sha256 = hashlib.sha256(binascii.unhexlify(first_sha256)).hexdigest()
        final_key = binascii.unhexlify(extended_key + second_sha256[:8])
        wif = base58.b58encode(final_key).decode('utf-8')
        wifs.append(wif)
    return wifs

def private_keys_to_addresses(private_keys):
    addresses = []
    for private_key_hex in private_keys:
        sk = ecdsa.SigningKey.from_string(binascii.unhexlify(private_key_hex), curve=ecdsa.SECP256k1)
        vk = sk.get_verifying_key()
        public_key = b'\x04' + vk.to_string()
        hash160 = hashlib.new('ripemd160')
        hash160.update(hashlib.sha256(public_key).digest())
        hash160 = hash160.digest()
        address = base58.b58encode_check(b"\x00" + hash160).decode('utf-8')
        addresses.append(address)
    return addresses

async def fetch_balance(session, bitcoin_address, counter, private_key_hex, result_list):
    url = f'https://bitcoin.atomicwallet.io/api/v2/address/{bitcoin_address}'
    
    while True:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    balance = int(data.get('balance', 0))
                    if balance > 0:
                        private_key_wif = private_keys_to_wifs([private_key_hex])[0]

                        with open('find.txt', 'a') as file:
                            file.write(f"Count: {counter}. Address: {bitcoin_address}: {balance} BTC. Details written to find.txt\n")
                            file.write(f"Private Key WIF: {private_key_wif}\n")
                            file.write(f"Private Key Hex: {private_key_hex}\n\n")

                        print(f"{Fore.BLUE}Count: {Fore.WHITE}{counter}{Style.RESET_ALL}. {Fore.YELLOW}Address: {Fore.GREEN}{bitcoin_address}{Fore.BLUE}: {Fore.RED}{balance} BTC{Style.RESET_ALL}. Details written to find.txt")

                        # Ajouter les détails à la liste des résultats
                        result_list.append({'private_key_wif': private_key_wif,
                                            'private_key_hex': private_key_hex,
                                            'address': bitcoin_address,
                                            'balance': balance})
                        break  # Break out of the loop if balance is obtained
                    else:
                        print(f"{Fore.BLUE}Count: {Fore.WHITE}{counter}{Style.RESET_ALL}. {Fore.YELLOW}Address: {Fore.GREEN}{bitcoin_address}{Fore.BLUE}: {Fore.RED}{balance} BTC{Style.RESET_ALL}. {Fore.YELLOW}No action taken.{Style.RESET_ALL}")
                        break  # Break out of the loop if balance is obtained but is zero
                else:
                    print(f"Failed to fetch balance for address {bitcoin_address}. Status code: {response.status}")
        except asyncio.TimeoutError:
            print(f"Timeout error for address {bitcoin_address}. Retrying...")
        except Exception as e:
            print(f"An error occurred for address {bitcoin_address}: {str(e)}. Retrying...")

async def main():
    result_list = []
    counter = 1

    while True:
        first_private_key = generate_private_key()
        next_private_keys = generate_next_private_keys(first_private_key, 1000)

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_balance(session, private_keys_to_addresses([private_key])[0], counter + i, private_key, result_list)
                     for i, private_key in enumerate(next_private_keys)]

            counter += 1000
            await asyncio.gather(*tasks)

        # Introduce a delay between iterations (for example, 60 seconds)
        await asyncio.sleep(0.000000000000000000000000000000000000000000000000000000000000000001)

if __name__ == "__main__":
    asyncio.run(main())