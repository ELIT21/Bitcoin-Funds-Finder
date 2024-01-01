import os
import codecs
import hashlib
import base58
import ecdsa
import aiohttp
import asyncio

async def generate_private_key():
    return os.urandom(32).hex()

def private_key_to_wif(private_key_hex: str, compressed: bool = False) -> str:
    if compressed:
        extended_key = "80" + private_key_hex + "01"  # Add compression flag
    else:
        extended_key = "80" + private_key_hex
    first_sha256 = hashlib.sha256(codecs.decode(extended_key, 'hex')).hexdigest()
    second_sha256 = hashlib.sha256(codecs.decode(first_sha256, 'hex')).hexdigest()
    final_key = codecs.decode(extended_key + second_sha256[:8], 'hex')
    return base58.b58encode(final_key).decode('utf-8')

def private_key_to_address(private_key_hex: str, compressed: bool = False) -> str:
    sk = ecdsa.SigningKey.from_string(codecs.decode(private_key_hex, 'hex'), curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()
    
    if compressed:
        public_key = vk.to_string('compressed')
    else:
        public_key = b'\x04' + vk.to_string()

    hash256 = hashlib.sha256(public_key).digest()
    hash160 = hashlib.new('ripemd160')
    hash160.update(hash256)
    hash160 = hash160.digest()

    return base58.b58encode_check(b"\x00" + hash160).decode('utf-8')

async def check_balance_with_retry(session, address):
    api_url = f'https://bitcoin.atomicwallet.io/api/v2/address/{address}'
    
    while True:
        async with session.get(api_url) as response:
            if response.status == 200:
                data = await response.json()
                return str(data.get('balance', 0))
            else:
                print(f"Error checking balance for address {address}. Status code: {response.status}")
                await asyncio.sleep(1)  # Wait for 1 second before retrying

def write_to_file(filename, content):
    with open(filename, 'a') as file:
        file.write(content + '\n')

async def process_address(session, address, compressed=True):
    balance = await check_balance_with_retry(session, address)
    print(f"{'Compressed' if compressed else 'Uncompressed'} Address: {address}, Balance: {balance}")

    if int(balance) > 0:
        private_key = await generate_private_key()
        wif_key = private_key_to_wif(private_key, compressed)
        uncompressed_address = private_key_to_address(private_key, compressed=False)

        write_to_file('find.txt', f"Compressed Address: {address}")
        write_to_file('find.txt', f"Private Key (WIF Compressed): {wif_key}")
        write_to_file('find.txt', f"Balance (Compressed): {balance}")
        
        write_to_file('find.txt', f"Uncompressed Address: {uncompressed_address}")
        write_to_file('find.txt', f"Private Key (WIF Uncompressed): {private_key_to_wif(private_key)}")
        write_to_file('find.txt', f"Balance (Uncompressed): {await check_balance_with_retry(session, uncompressed_address)}")

async def main():
    async with aiohttp.ClientSession() as session:
        counter = 0

        while True:
            # Generate 1000 private keys
            private_keys = [await generate_private_key() for _ in range(10000)]

            # Generate 1000 compressed and 1000 uncompressed addresses using the same set of private keys
            compressed_addresses = [private_key_to_address(private_key, compressed=True) for private_key in private_keys]
            uncompressed_addresses = [private_key_to_address(private_key) for private_key in private_keys]

            # Run checks for compressed and uncompressed addresses simultaneously
            await asyncio.gather(
                *[process_address(session, address, compressed=True) for address in compressed_addresses],
                *[process_address(session, address, compressed=False) for address in uncompressed_addresses]
            )

            # Increment counter by 2000
            counter += 20000
            print(f"Total iterations: {counter}")

            # Wait for 1 hour before the next run
            await asyncio.sleep(0.0000000000000000000000000000000000000000000000000000000000000000001)  # 3600 seconds = 1 hour

if __name__ == "__main__":
    # Run the main asynchronous loop
    asyncio.run(main())