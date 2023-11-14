# impot 'asyncio' for asynchronous operations, 'logging', for logging messages, and websockets for bidirectional communication
import asyncio
import logging
import websockets


# imports the ChargePoint class from the ocpp 2.0.1 specification and the call module which contains the message formats for various OCPP calls.
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call


# Initialize the logging module to display logs of severity INFO and above
logging.basicConfig(level=logging.INFO)

# Define a new class which inheirts from the imported ChargePoint class from the OCPP library. 
class ChargePoint(cp):
    async def send_heartbeat(self, interval):  # asynchronous method within the ChargePoint class to send a heartbeat message. 
        request = call.HeartbeatPayload()      # request(call.HeartbeatPayload()) constructs a payload for the heartbeat message
        while True:                            # infinite loop to send the heartbeat request and sleep for a specified duration
            await self.call(request)           # self.call(request) sends a heartbeat request to the central system and requets 
            await asyncio.sleep(interval)      # asyncio.sleep(interval) sleeps for the specified duration (specified in the central system)

    async def send_boot_notification(self):   # asynchronous method within the ChargePoint class which sends a boot notification.
        request = call.BootNotificationPayload(  # constructs a payload for the boot notification with parameters specifying the:
            charging_station={"model": "Wallbox XYZ",   
                              "vendor_name": "anewone",   # charging station details
                              "serial_number":"123445",
                              "firmware_version":"1.2.3"},
            reason="PowerUp",                             # and the reason for the boot notification
        )
        response = await self.call(request)               # sends the boot notification request and awaits a response

        
        # Checks if the response status from the central system is "Accepted". If so, it prints a message indicating the connection 
        # and then starts sending heartbeat messages using the 'send_heartbeat' function with the interval specified in the boot notification response.
        if response.status == "Accepted":
            print("Connected to central system.")
            await self.send_heartbeat(response.interval)

# Defines the main asynchronous function whcih connects to the central system using the websockets library and starts the ChargePoint.
async def main():

    # This block asyncrhonously establishes a websocket (client) connection to the given URL with a specified subprotocol.
    # The ws variable is the established websocket connectin.
    async with websockets.connect(
        "ws://localhost:9000/CP_1", subprotocols=["ocpp2.0.1"]
    ) as ws:

        charge_point = ChargePoint("CP_1", ws)  # An instance of the ChargePoint class is created with ID "CP_1" and the websocket connection.
        
        # Two tasks, charge_point.start() and charge_point.send_boot_notification(), are started concurrently using asyncio.gather()
        await asyncio.gather(
            charge_point.start(), charge_point.send_boot_notification()
        )


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())  # starts the simulated chargepoint by asynchronously running the main function.