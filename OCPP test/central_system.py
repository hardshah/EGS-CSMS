# impot 'asyncio' for asynchronous operations, 'logging', for logging messages, and 'datatime' for working with date and time
import asyncio
import logging
from datetime import datetime

# import the websockets library
import websockets

# import required modules and classes from the ocpp library related to routing, the core ChargePoint class for version 2.0.1 and call_results for responding to ocpp calls from charge points
from ocpp.routing import on, after
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call, call_result

# set up basic config for loggging. The logging level is set to 'INFO' so any logs with a severity of INFO or higher will be displayed
logging.basicConfig(level=logging.INFO)


class ChargePoint(cp):  # A new class 'ChargePoint' is defined which inherits from the 'ChargePoint' Class from OCPP.v201
    @on("BootNotification") # The @on decorator defines a handler for the 'BootNotification' message. 
                            # This means that when a connected CP sends a boot notification, the on_boot_notofication will execute
   # This function constructs a response payload for the boot notofication, providing the current UTC time, an interval of 10 seconds, and a status of "Accepted".
   # This payload is sent back to the charge point. 
    def on_boot_notification(self, charging_station, reason, **kwargs):
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(), interval=10, status="Accepted"
        )

    # Similarily, a handler is defined for the 'Heartbeat' message. When this message is recieved, the code primts "Got a HeartBeat!"
    # and sends back a response containing the current UTC time. 
    @on("Heartbeat")
    def on_heartbeat(self):
        print("Got a Heartbeat!")
        return call_result.HeartbeatPayload(
            current_time=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        )
    
    ''' Next step is to add more handlers for other messaged defined in OCPP2.0.1 such as transaction (start/stop).'''

    @on("MeterValues")
    async def on_meter_values(self, evse_id, meter_value, **kwargs):
        logging.info("Metervalues received: %s", meter_value)

        return call_result.MeterValuesPayload()
    
    @on("TransactionEvent")
    async def on_transaction_event(self, event_type,transaction_info, **kwargs):
        logging.info("TransactionEvent received: %s", event_type)

        return call_result.TransactionEventPayload()
    
    @after("TransactionEvent")
    async def after_transaction_event(self, event_type, transaction_info, **kwargs):
        logging.info("poop")

        if event_type == "Started":
            logging.info("testpoop")
            await self.start_transaction(transaction_info['transaction_id'])
        else:
            logging.info("Error processing transaction request")


    async def start_transaction(self, id_token):
        request = call.RequestStartTransactionPayload(
            id_token={
                "id_token": id_token,
                "type":"Central"
            },
            remote_start_id=1023,
            evse_id=1,
            custom_data={
                'vendorId': 'test vendor',
                "current time": datetime.utcnow().isoformat()
            }
            # id_tag='1',
            # meter_start=0,          # Initial Energy meter value / integer
            # timestamp=datetime.utcnow().isoformat()
        )
        response = await self.call(request)
        # await self.send_status_notification(ChargePointErrorCode.ev_communication_error, ChargePointStatus.preparing)
        if response.status == "Accepted":
            logging.info("Started Charging")
            # await self.send_status_notification(ChargePointErrorCode.no_error, ChargePointStatus.charging)
            return response.transaction_id
        else:
            logging.error("Problems with starting the charge process!")


# This is an aysnchronous function designed to handle new charge point connections. It will be invoked whenever a new websocket client connects to the server.
async def on_connect(websocket, path): 
    """For every new charge point that connects, create a ChargePoint
    instance and start listening for messages.
    """
    # This block attempts to fetch the 'Sec-Websocket-Protocol' header from the connecting client's request headers, which indicates which
    # OCPP version(s) the client supports. If this header is absent a key error will be raised. 
    try:
        requested_protocols = websocket.request_headers["Sec-WebSocket-Protocol"]
    except KeyError:
        logging.info("Client hasn't requested any Subprotocol. " "Closing Connection")  # When the Key Error is raised, the error is logged and the websocket connection is closed
        return await websocket.close()
    
    
    # This block chekcs if a common OCPP version (subprotocol) has been agreed upon between client and server. If so, it logs the matched version.
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        # In the websockets lib if no subprotocols are supported by the
        # client and the server, it proceeds without a subprotocol,
        # so we have to manually close the connection.
        logging.warning(
            "Protocols Mismatched | Expected Subprotocols: %s,"
            " but client supports %s | Closing connection",
            websocket.available_subprotocols,
            requested_protocols,
        )
        return await websocket.close()  # close the connection if OCPP versions are mismatched

    charge_point_id = path.strip("/")  # The connected charge point's ID is extracted from the URL's path (path component of URL).
    charge_point = ChargePoint(charge_point_id, websocket) # An instance of the previously defined ChargePoint class is created using the extracted
                                                           # charge point ID and the established websocket connection

    await charge_point.start() # The start method of the ChargePoint instance is called. This method will handle incoming OCPP messages from the connected charge point

# The main asyncrhonous function of the script, responsible for setting up and running the OCPP server.
async def main(): 
    #  deepcode ignore BindToAllNetworkInterfaces: <Example Purposes>
    
    # This block starts the websocket server, binding it to all network interfaces ('0.0.0.0') on port 9000. The on_connect function 
    # will handle new connections. The server expects clients to support the OCPP 2.0.1 subprotocol.
    server = await websockets.serve(                             
        on_connect, "0.0.0.0", 9000, subprotocols=["ocpp2.0.1"]
    )

    # A log message indiciated the server has started, and then the server runs indefinitley, waiting for incoming connections. The wait_closed()
    # method keeps the server running until it is manually closed.
    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__": # This condition checks if the script is being ran as a standalone program (and not imported as a module elsewhere)
    asyncio.run(main())    # The main asyncrhonous function is executed, starting the server. The 'asynchio.run()' method is the standard way
                           # to initiate and run asynchronous tasks in python 3.7 and beyond. 