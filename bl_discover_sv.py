import asyncio
from bleak import BleakScanner, BleakClient

DEVICE_MAC_ADDRESS = "94:A0:81:D0:47:E4"


async def discover_services_and_characteristics():
    async with BleakClient(DEVICE_MAC_ADDRESS) as client:
        if await client.is_connected():
            print(f"Connected to : {DEVICE_MAC_ADDRESS}")
            
            services = await client.get_services()
            print("All services and UUID:")
            
            for service in services:
                print(f"- Service: {service.uuid}")
                for char in service.characteristics:
                    print(f"  - Characteristic: {char.uuid} (Properties: {char.properties})")
        else:
            print("Cannot connect to device.")


asyncio.run(discover_services_and_characteristics())
