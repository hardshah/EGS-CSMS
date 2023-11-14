# import 'asyncio' for asynchronous operations, 'logging', for logging messages, and 'datatime' for working with date and time
import asyncio
import logging
from datetime import datetime
import smart_meter 
# from DB.db import validate_CP_connection, CP_db, update_CP_status, get_charging_cps, transaction_db, 
import DB.db as db

# import the websockets library
import websockets

# import required modules and classes from the ocpp library related to routing, the core ChargePoint class for version 2.0.1 and call_results for responding to ocpp calls from charge points
from ocpp.routing import on, after
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call, call_result

# set up basic config for loggging. The logging level is set to 'INFO' so any logs with a severity of INFO or higher will be displayed
logging.basicConfig(level=logging.INFO)


POWERCAPACITY = 45000
MAX_LOGS_PER_CP = 100
meter_values_store = {}
chargepoint_logs = {}
active_cps = set()

def append_to_cp_log(cp_id, log_message):
    global chargepoint_logs
    if cp_id not in chargepoint_logs:
        chargepoint_logs[cp_id] = []

    chargepoint_logs[cp_id].append({
        'timestamp':datetime.utcnow().isoformat(),
        'message':log_message
    })

    # Remove oldest logs if the number of logs exceeds the limit
    while len(chargepoint_logs[cp_id]) > MAX_LOGS_PER_CP:
        chargepoint_logs[cp_id].pop(0)

    logging.info(f"Logged for {cp_id}: {log_message}")


class ChargePoint(cp):  # A new class 'ChargePoint' is defined which inherits from the 'ChargePoint' Class from OCPP.v201

    def __init__(self, charge_point_id, websocket):
        super().__init__(charge_point_id, websocket)
        self.transaction_id = ""
   


    @on("BootNotification") # The @on decorator defines a handler for the 'BootNotification' message. 
                            # This means that when a connected CP sends a boot notification, the on_boot_notofication will execute
   # This function constructs a response payload for the boot notofication, providing the current UTC time, an interval of 10 seconds, and a status of "Accepted".
   # This payload is sent back to the charge point. 
    def on_boot_notification(self, charging_station, reason, **kwargs):
        append_to_cp_log(self.id, f"BootNotification Recieved: {[charging_station, reason]}")
        response_payload = call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(), interval=10, status="Accepted"
        )
        append_to_cp_log(self.id, f"Responsed to BootNotification with: {response_payload}")
        return response_payload

    # Similarily, a handler is defined for the 'Heartbeat' message. When this message is recieved, the code primts "Got a HeartBeat!"
    # and sends back a response containing the current UTC time. 
    @on("Heartbeat")
    def on_heartbeat(self):
        print("Got a Heartbeat!")
        append_to_cp_log(self.id, f"HeartBeat Recieved")
        response_payload = call_result.HeartbeatPayload(
            current_time=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        )
        append_to_cp_log(self.id, f"Responsed to Heartbeat with: {response_payload}")
        return response_payload
    
    @on("MeterValues")
    async def on_meter_values(self, evse_id, meter_value, **kwargs):
        
        cp_id = self.id

        meter_data = meter_value[0]
        timestamp = meter_data['timestamp']
        sampled_values = {}
        for value in meter_data['sampled_value']:
            measurand = value['measurand']
            original_value = value['value']
            unit = value['unit_of_measure']['unit']

            if measurand in ('Power.Active.Import','Energy.Active.Import.Register') and unit in ('W','Wh'):
                converted_value = original_value/1000
                if unit == 'W':
                    unit = "kW"
                elif unit == 'Wh':
                    unit = 'kWh'
                sampled_values[measurand] = [converted_value, unit]
            else:
                sampled_values[measurand] = [original_value, unit]

        meter_dict = {
            'timestamp': timestamp,
            **sampled_values
        }

        meter_values_store[cp_id] = meter_dict
        # Respond to the received meter values without any additional data.
        append_to_cp_log(cp_id, f"Meter values recieved: {meter_value}")
        response_payload =call_result.MeterValuesPayload()
        append_to_cp_log(cp_id, f"Responded to Meter values with: {response_payload}")
        return response_payload

    @on("TransactionEvent")
    async def on_transaction_event(self, event_type, transaction_info, **kwargs):
        # Log the event type received during a transaction.
        logging.info("TransactionEvent received: %s", event_type)
        append_to_cp_log(self.id, f"TransactionEvent recieved: {event_type} {transaction_info}")
        # Respond to the transaction event without providing extra data.
        response_payload = call_result.TransactionEventPayload()
        append_to_cp_log(self.id, f"Responded to transactionevent with: {response_payload}")
        return response_payload
    
    async def set_charging_profile(self, limit,**kwargs):
        request = call.SetChargingProfilePayload(
            evse_id=1,
            charging_profile={
                "id":1,
                "stack_level": 1,
                "charging_profile_purpose": "ChargingStationMaxProfile",
                "charging_profile_kind": "Absolute",
                "charging_schedule": [{"id": 1,
                                      "start_schedule": datetime.utcnow().isoformat(),  # Example start time
                                      "charging_rate_unit": "A",  # Amperes
                                      "charging_schedule_period": [{
                                          "start_period": 0,
                                          "limit": limit,
                                      }]
            }]
            }
        )
        response = await self.call(request)
        append_to_cp_log(self.id, f"charging profile sent: {limit} A")


    @after("TransactionEvent")
    async def after_transaction_event(self, event_type, transaction_info, **kwargs):
        
        # Check the type of transaction event and act accordingly.
        if event_type == "Started":
            # Log a message and initiate a transaction using the received transaction ID.
            await self.start_transaction(transaction_info['transaction_id'])
        elif event_type == "Ended":
            # Log a message and stop the transaction using the received transaction ID.
            logging.info("Ended Charging")
            await self.stop_transaction(transaction_info['transaction_id'])
        else:
            # Log an error message if the transaction event type is not recognized or cannot be processed.
            logging.info("Error processing transaction request")

    async def start_transaction(self, id_token):
        # Create a request payload to start a transaction with provided ID token and additional custom data.
        request = call.RequestStartTransactionPayload(
            id_token={
                "id_token": id_token,
                "type":"Central"
            },
            remote_start_id=1023,
            evse_id=1,
            # custom_data={
            #     'vendorId': 'test vendor',
            #     "current time": datetime.utcnow().isoformat()
            # }
        )
        append_to_cp_log(self.id, f"RequestStartTransaction sent: {request}")
        # Send the request and wait for a response.
        response = await self.call(request)
        
        # Check the status of the response and log the results or potential errors.
        if response.status == "Accepted":
            logging.info("Started Charging")
            self.is_charging=True
            append_to_cp_log(self.id, f"Started Charging: {response}")
            db.update_CP_status(self.id, "charging")
            active_cps.add(self)
            await db.insert_transaction_in_db(id_token,self.id)
            await create_charging_profiles()
            # return response.transaction_id
        else:
            logging.error("Problems with starting the charge process!")
            append_to_cp_log(self.id, "Problems with starting the charge process!")

    async def stop_transaction(self,transaction_id):
        # Create a request payload to stop a transaction, identifying it using the provided transaction ID.
        request = call.RequestStopTransactionPayload(
            transaction_id=transaction_id
        )
        # Send the request and wait for a response.
        append_to_cp_log(self.id, f"RequestStopTransaction sent: {request}")
        response = await self.call(request)
        
        # Check the status of the response, logging either the stoppage of charging or an error.
        if response.status == "Accepted":
            logging.info("Stopped charging")
            self.is_charging=False
            append_to_cp_log(self.id, f"Stopped charging: {response}")
            db.update_CP_status(self.id, "available")
            active_cps.discard(self)
            await db.log_stop_transaction_in_db(transaction_id)
            await create_charging_profiles()
            # return response.custom_data['transaction_id']
        else:
            logging.error("Problems with stopping the charge process!")
            append_to_cp_log(self.id, "Problems with stopping the charging process!")

async def create_charging_profiles():
    if len(active_cps) == 0:
        limit = POWERCAPACITY - smart_meter.get_demand()
    else:
        limit = ((POWERCAPACITY - smart_meter.get_demand())/len(active_cps))/220
        for ChargePoint in active_cps:
            await ChargePoint.set_charging_profile(limit)
    logging.info("Charging profiles sent!")
    logging.info(limit)


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
    
   
    #This block checks to make sure the chargepoint id exists in the database
    requested_id = path.strip("/")
    if not db.validate_CP_connection(requested_id):
        logging.warning("CP_id %s is not registered in the database. Closing connection.", requested_id)
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
    db.update_CP_status(charge_point_id, "available")
     
    try:                                                      # charge point ID and the established websocket connection
        await charge_point.start() # The start method of the ChargePoint instance is called. This method will handle incoming OCPP messages from the connected charge point
    finally:
        db.update_CP_status(charge_point_id, "offline")
        if charge_point_id in meter_values_store:
            del meter_values_store[charge_point_id]


async def start_websocket_server():
    server = await websockets.serve(on_connect, '0.0.0.0', 9000, subprotocols=["ocpp2.0.1"])
    await server.wait_closed()




'''
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
'''