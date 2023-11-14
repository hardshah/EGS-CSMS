# MIT License
#
# Copyright (c) 2019 The Mobility House
# https://github.com/mobilityhouse/ocpp
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Usage
# python3.9 ocpp_16_charge_point_sim.py <OCPP SERVER IP ADDRESS> <OCPP SERVER PORT> <WS PATH> <CHARGING POINT ID> <VENDOR NAME (OPTIONAL)>


import asyncio
import logging
from datetime import datetime, timedelta
import websockets
import sys
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import decimal

from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call, call_result
from ocpp.routing import on, after
from ocpp.v16.enums import *
from ocpp.v16.datatypes import MeterValue, SampledValue
from ocpp.v201.datatypes import SampledValueType, MeterValueType
# from pynput import keyboard
import threading
import keyboard
import uuid

logging.basicConfig(level=logging.INFO)
CP_VENDOR = "Test"
# Global Variables for Configuration Values
config_heartbeat_interval = "10"
charging_schedule_allowed_charging_rate_unit = "['A', 'W']"
charging_schedule_allowed_charging_rate_unit_wallbox = "['A']"
config_clock_aligned_data_interval = 5
meter_value_sample_interval = 0
config_meter_values = ["Current.Import",
                       "Voltage",
                       "Power.Active.Import",
                       "Energy.Active.Import.Register",
                       "Power.Offered",
                       "Temperature",
                       "SoC"]
# End Configuration Values


cp_keys = {
    "CP_1": {'start': 'a', 'stop': 'b'},
    "CP_2": {'start':'c','stop': 'd'},
    "CP_3": {'start':'e','stop':'f'},
    "CP_4": {'start': 'g', 'stop': 'h'},
    "CP_5": {'start': 'i', 'stop':'j'}
}

# Meter Values
meter_value_power_active_import = SampledValueType(value=0, context='Sample.Periodic', 
                                                measurand='Power.Active.Import', location=None, unit_of_measure={'unit':'W'})
meter_value_voltage_L1 = SampledValueType(value=0, context='Sample.Periodic',
                                       measurand='Voltage',  phase='L1', location=None, unit_of_measure={'unit': 'V'})
meter_value_voltage_L2 = SampledValueType(value=0, context='Sample.Periodic',
                                       measurand='Voltage',  phase='L2', location=None, unit_of_measure={'unit':'V'})
meter_value_voltage_L3 = SampledValueType(value=0, context='Sample.Periodic',
                                       measurand='Voltage',  phase='L3', location=None, unit_of_measure={'unit':'V'})
meter_value_energy_active_import_register = SampledValueType(
    value=8567, context='Sample.Periodic',  measurand='Energy.Active.Import.Register', phase=None, location=None, unit_of_measure={'unit':'Wh'})
meter_value_power_offered = SampledValueType(
    value=0, context='Sample.Periodic',  measurand='Power.Offered', phase=None, location=None, unit_of_measure={'unit':'W'})
# meter_value_temperature = SampledValueType(value=50, context='Sample.Periodic',
#                                         measurand='Temperature', phase=None, location=None, unit_of_measure={'unit':'Celsius'})
meter_value_soc = SampledValueType(value=57, context='Sample.Periodic',
                                measurand='SoC', phase=None, location=None, unit_of_measure={'unit':'Percent'})

charging_meter_value_power_active_import_value = 7400
charging_meter_value_voltage_L1 = 220
charging_meter_value_voltage_L2 = 220
charging_meter_value_voltage_L3 = 220
charging_meter_value_energy_active_import_register_value = 18569
charging_meter_value_power_offered_value = 0.25
charging_meter_value_temperature_value = 50
charging_meter_value_soc_value = 57

stopped_meter_value_power_active_import_value = 0
stopped_meter_value_voltage_L1 = 0
stopped_meter_value_voltage_L2 = 0
stopped_meter_value_voltage_L3 = 0
stopped_meter_value_energy_active_import_register_value = 18569
stopped_meter_value_power_offered_value = 0.25
stopped_meter_value_temperature_value = 0
stopped_meter_value_soc_value = 57

# End Meter Values
scheduler = None
last_known_power_limit = None


def restore_from_limit_power():
    global last_known_power_limit
    global meter_value_power_active_import
    if last_known_power_limit and float(meter_value_power_active_import.value) != 0:
        meter_value_power_active_import.value = str(last_known_power_limit)

# Function that listens for keyboard events and sends messages to a charge point based on the key pressed.
async def on_press(CP, start_key, stop_key):
    while True:  # Infinite loop to continuously check for key presses.
        # If the 'p' key is pressed, send a "Started" transaction event to the charge point and pause for 0.5 seconds.
        if keyboard.is_pressed(start_key):  
            await CP.send_transaction_event("Started")
            await asyncio.sleep(0.5)  # Wait for 0.5 seconds to avoid sending multiple events on a single key press.
        # If the 'o' key is pressed, send an "Ended" transaction event to the charge point and pause for 0.5 seconds.
        elif keyboard.is_pressed(stop_key):  
            await CP.send_transaction_event("Ended")
            await asyncio.sleep(0.5)  # Wait for 0.5 seconds to avoid sending multiple events on a single key press.
        await asyncio.sleep(0.1)  # Sleep for 0.1 seconds before checking for key presses again to avoid high CPU usage.

async def generate_transaction_id() -> str:
    """
    Asynchronously generates a random transaction ID suitable for OCPP 2.0.1 transactions.

    :return: A unique transaction ID string.
    """
    # Simulate some async I/O operation if needed, e.g., checking a database for existing IDs.
    await asyncio.sleep(0) # This is just a placeholder for actual async I/O operations.

    # Generate a random UUID4 string as the transaction ID.
    transaction_id = str(uuid.uuid4())

    return transaction_id

    



class ChargePoint(cp):
    def __init__(self,id,connection):
        super().__init__(id,connection)
        self.transactionID=""
        self.transactionstatus=""
        self.transactionstate=False
    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charging_station={"model": "Wallbox XYZ",   
                              "vendor_name": "anewone",   # charging station details
                              "serial_number":"123445",
                              "firmware_version":"1.2.3",
                            #   "iccid":'FED42',
                            #   "imsi":"1234ABCD",
                            #   "meter_serial_number":"1A2B3C4D",
                            #   "meter_type":"test_meter"
                             },
            reason="PowerUp",                       
            # charge_point_model="Python ",
            # charge_point_vendor=CP_VENDOR,
            # charge_box_serial_number="1337",
            # charge_point_serial_number="001",
            # firmware_version="0.0.1",
            # iccid="FED42",
            # imsi="1234ABCD",
            # meter_serial_number="1A2B3C4D",
            # meter_type="test_meter"
        )

        response = await self.call(request)

        if response.status == "Accepted":
            logging.info("Connected to central system.")
        elif response.status == "Rejected":
            logging.info("Central system rejected the connection!")


    async def change_availablity(self):
        request = call.ChangeAvailabilityPayload(
            connector_id=1,
            type=AvailabilityType.operative  # .inoperative
        )

        response = await self.call(request)

        if response.status == AvailabilityType.operative:
            logging.info("System available.")
        elif response.status == AvailabilityType.operative: # should be .inoperative?
            logging.info("System not available.")

    async def send_heartbeat(self):
        while True:
            try:
                request = call.HeartbeatPayload()
                await self.call(request)
            except websockets.exceptions.ConnectionClosedError:
                logging.error("WebSocket connection closed when sending heartbeat.")
                # Consider reconnection logic here if necessary
            except Exception as e:
                logging.error(f"Error during heartbeat: {str(e)}")
            await asyncio.sleep(int(config_heartbeat_interval))
                # Heartbeat rate in sec
            #     await asyncio.sleep(int(config_heartbeat_interval))
            # except:
            #     raise

    async def send_authorize(self):     # sending the request has not been implemented
        request = call.AuthorizePayload(
            id_tag='abcdefghijklmnopqrst'
        )

    async def periodic_meter_values(self):
        global config_clock_aligned_data_interval
        while True:  # Infinite loop to send meter values periodically.
            try:
                # Attempt to send meter values and then wait for a response.
                response = await self.send_meter_values()
                # Sleep for a specified amount of time before sending the next set of meter values.
                await asyncio.sleep(int(config_clock_aligned_data_interval))
            except:  # Catch any exception that occurs in the try block.
                raise  # Re-raise the caught exception.

    async def send_transaction_event(self,event_type):
        # Prepare a payload with transaction event details.
        if event_type == "Started":
            transaction_id = await generate_transaction_id()
            self.transactionID = transaction_id
        else:
            transaction_id = self.transactionID


        request = call.TransactionEventPayload(
            # Various parameters defining the event.
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            trigger_reason="Authorized",
            seq_no=1,
            transaction_info={
                "transaction_id": transaction_id,
                "charging_state":"Charging"
            }
        )
        # Send the prepared request and log the action.
        await self.call(request)
        logging.info("Transaction Event request was sent!")

    @on("RequestStartTransaction") 
    async def on_start_transaction(self, id_token, **kwargs ):
        logging.info("start Transaction received: %s", id_token)
        # Update global variables upon transaction start. Presumably, to update meter readings.
        global meter_value_power_active_import
        global meter_value_voltage_L1
        global meter_value_voltage_L2
        global meter_value_voltage_L3
        global meter_value_energy_active_import_register
        global meter_value_power_offered
        global meter_value_soc

        # Assign new values to the global variables.
        meter_value_power_active_import.value = charging_meter_value_power_active_import_value
        meter_value_voltage_L1.value = charging_meter_value_voltage_L1
        meter_value_voltage_L2.value = charging_meter_value_voltage_L2
        meter_value_voltage_L3.value = charging_meter_value_voltage_L3
        meter_value_energy_active_import_register.value = charging_meter_value_energy_active_import_register_value
        meter_value_power_offered.value = charging_meter_value_power_offered_value
        # meter_value_soc.value = charging_meter_value_soc_value

        # Assign received transactionID to the instance.
        self.transactionID = id_token['id_token']
        self.transactionstate= True

        # Respond to the request start transaction by accepting it and providing details in custom data.
        return call_result.RequestStartTransactionPayload(
            status = "Accepted",
            transaction_id= id_token['id_token'],
            # custom_data={
            #     'vendorId': 'test vendor',
            #     "current time": datetime.utcnow().isoformat()
            # }
        )

    @on("RequestStopTransaction")
    async def on_stop_transaction(self, transaction_id):
        # Check if the received transaction_id matches the ongoing one.
        if transaction_id == self.transactionID:
            self.transactionstatus = "Accepted"  # Update status as Accepted.
            self.transactionstate=False
            logging.info("Stop Transaction received!, stopping session")  
        else:  # Log an error if IDs do not match.
            self.transactionstatus = "Rejected"
            logging.error("Transaction ID does not match, failed to stop charging session!")

        # Respond to the request to stop the transaction with status and custom data.
        return call_result.RequestStopTransactionPayload(
            status=self.transactionstatus,
            # status_info=self.transactionID
        #     custom_data={
        #         'vendorId': 'test vendor',
        #         'transaction_id': self.transactionID,
        #         "current time": datetime.utcnow().isoformat()
        #     }
         )

    @after("RequestStopTransaction")
    async def after_stop_transaction(self,transaction_id):
        # If the transaction was accepted, update meter reading variables.
        if self.transactionstatus == "Accepted":
            # Update global variables upon stopping the transaction.
            global meter_value_power_active_import
            global meter_value_voltage_L1
            global meter_value_voltage_L2
            global meter_value_voltage_L3
            global meter_value_energy_active_import_register
            global meter_value_power_offered
            global meter_value_soc

            # Assign new values to the global variables.
            meter_value_power_active_import.value = stopped_meter_value_power_active_import_value
            meter_value_voltage_L1.value = stopped_meter_value_voltage_L1
            meter_value_voltage_L2.value = stopped_meter_value_voltage_L2
            meter_value_voltage_L3.value = stopped_meter_value_voltage_L3
            meter_value_energy_active_import_register.value = stopped_meter_value_energy_active_import_register_value
            meter_value_power_offered.value = stopped_meter_value_power_offered_value
            # meter_value_soc.value = stopped_meter_value_soc_value
        else:
            # Log an error if transaction failed to stop.
            logging.error("Transaction failed to stop charging session!")

            
    async def charging_session(self):
        logging.info("charging session function has been called")
        global meter_value_soc
        while True:
            logging.info("while loop triggered")
            if self.transactionstate:
                meter_value_soc.value += 1
            await asyncio.sleep(10)
    
    
    async def send_status_notification(self, err_code, status):
        if err_code == "no_error":
            error_code = ChargePointErrorCode.no_error
        else:
            error_code = err_code

        request = call.StatusNotificationPayload(
            connector_id=1,
            error_code=error_code,
            status=status
        )
        response = await self.call(request)

        # Define an asynchronous function named `send_meter_values` within a class (presumably representing a charge point, given the `self` parameter).
    async def send_meter_values(self):
        
        # Create a payload for a MeterValues message using the `MeterValuesPayload` class. This message might be defined by an OCPP library and is used to send meter readings to the central system.
        # Various values, like energy usage and voltage, can be included in a MeterValues message. 
        # Here it includes a single MeterValue object which contains a timestamp and multiple sampled values.
        # [Note: The variables like `meter_value_power_active_import`, `meter_value_voltage_L1`, etc. should be defined elsewhere in your code, before this payload is constructed.]
        request = call.MeterValuesPayload(
            evse_id=1,  # Set the EVSE (Electric Vehicle Supply Equipment) ID to 1. This identifies which EVSE the meter values are for.
            meter_value=[  # Start a list of MeterValue objects. Each object represents a set of readings from the meter.
                MeterValue(
                    timestamp=datetime.utcnow().isoformat(),  # Set the timestamp for the meter reading to the current time in UTC, formatted as a string.
                    sampled_value=[  # Begin a list of sampled values. Each object in this list represents a single measurement from the meter.
                        meter_value_power_active_import,  # Include a measurement of active power import (the power currently being drawn by the EV).
                        meter_value_voltage_L1,  # Include a measurement of voltage on line 1.
                        meter_value_voltage_L2,  # Include a measurement of voltage on line 2.
                        meter_value_voltage_L3,  # Include a measurement of voltage on line 3.
                        meter_value_energy_active_import_register,  # Include a measurement of the total imported energy (e.g., kWh drawn by the EV since the start of the session).
                        meter_value_power_offered,  # Include a measurement of the power being offered by the EVSE.
                        # meter_value_temperature,  # [Commented Out] Optionally, include a measurement of the temperature.
                        meter_value_soc  # Include a measurement of the state of charge of the EV’s battery.
                    ]
                )
            ]
        )
        
        # Send the constructed MeterValues payload (request) as a call to the central system and await the response.
        # The actual sending and receiving of the message would be handled by the `call` method of the object, which is not provided in the snippet.
        response = await self.call(request)


    @on("SetChargingProfile")       # sets charging profile, very important for smart charging
    async def set_charging_profile(self, evse_id, charging_profile):
        logging.info("charging profile recieved")
        logging.info("charging profile: %s", charging_profile)
        return call_result.SetChargingProfilePayload(status="Accepted")
    
    @after("SetChargingProfile")
    async def config_charging_profile(self, evse_id, charging_profile):
        global meter_value_power_active_import
        global last_known_power_limit
        global scheduler
        unit = charging_profile["charging_schedule"][0]["charging_rate_unit"]
        limit = charging_profile["charging_schedule"][0]["charging_schedule_period"][0]["limit"]
        # duration = charging_profile["charging_schedule"][0]["duration"]

        if float(meter_value_power_active_import.value) > 0:
            if unit == "W" and limit:
                last_known_power_limit = meter_value_power_active_import.value
                meter_value_power_active_import.value = limit
            elif unit == "A" and limit:
                limit = meter_value_voltage_L1.value*limit
                last_known_power_limit = meter_value_power_active_import.value
                meter_value_power_active_import.value = limit
            # else:
            #     return call_result.SetChargingProfilePayload(
            #         status=ChargingProfileStatus.rejected
            #     )
        #     scheduler = AsyncIOScheduler()
        #     scheduler.add_job(restore_from_limit_power, 'date',
        #                       run_date=datetime.now()+timedelta(seconds=duration))
        #     scheduler.start()
        #     return call_result.SetChargingProfilePayload(
        #         status=ChargingProfileStatus.accepted
        #     )
        # else:
        #     return call_result.SetChargingProfilePayload(
        #         status=ChargingProfileStatus.rejected
        #     )

    @on(Action.ClearChargingProfile)
    async def clear_charging_profile(self, id, connector_id, charging_profile_purpose):
        global meter_value_power_active_import
        if last_known_power_limit:
            meter_value_power_active_import.value = last_known_power_limit
        return call_result.ClearChargingProfilePayload(
            status=ClearChargingProfileStatus.accepted
        )

    @on(Action.RemoteStartTransaction)
    async def on_remote_start_transaction(self, connector_id, id_tag):
        asyncio.gather(self.start_transaction())
        return call_result.RemoteStartTransactionPayload(
            status=RemoteStartStopStatus.accepted
        )

    @on(Action.RemoteStopTransaction)
    async def on_remote_stop_transaction(self, transaction_id):
        asyncio.gather(self.stop_transaction(transaction_id))
        return call_result.RemoteStopTransactionPayload(
            status=RemoteStartStopStatus.accepted
        )

    @on(Action.TriggerMessage)
    async def on_trigger_message(self, requested_message, **kwargs):
        return call_result.TriggerMessagePayload(
            status=TriggerMessageStatus.accepted
        )

    @on(Action.MeterValues)
    async def on_meter_values_conf(self, metervalues_conf):
        pass

    @after(Action.TriggerMessage)
    async def handle_trigger_message(self, requested_message):
        if requested_message == "Heartbeat":
            response = await self.send_heartbeat()
        elif requested_message == "BootNotification":
            response = await self.send_boot_notification()
        elif requested_message == "MeterValues":
            response = await self.send_meter_values()
        else:
            raise Exception("Unhandled Trigger Message Type: ",
                            requested_message)

    @on(Action.GetConfiguration)
    async def on_get_configuration(self):
        configuration_pairs = []
        configuration_pairs.append(
            {
                "key": "HeartbeatInterval",
                "readonly": False,
                "value": config_heartbeat_interval
            }
        )
        if CP_VENDOR == "Wall Box Chargers":
            configuration_pairs. append(
                {
                    "key": "ChargingScheduleAllowedChargingRateUnit",
                    "readonly": True,
                    "value": charging_schedule_allowed_charging_rate_unit_wallbox
                }
            )
        else:
            configuration_pairs. append(
                {
                    "key": "ChargingScheduleAllowedChargingRateUnit",
                    "readonly": True,
                    "value": charging_schedule_allowed_charging_rate_unit
                }
            )
        return call_result.GetConfigurationPayload(configuration_key=configuration_pairs)

    @on(Action.ChangeConfiguration)
    async def on_change_configuration(self, key, value):
        return call_result.ChangeConfigurationPayload(
            status=ConfigurationStatus.accepted
        )

    @after(Action.ChangeConfiguration)
    async def handle_change_configuration(self, key, value):
        if key == "HeartbeatInterval":
            global config_heartbeat_interval
            config_heartbeat_interval = value
        elif key == "MeterValuesAlignedData":
            pass
        elif key == "ClockAlignedDataInterval":
            global config_clock_aligned_data_interval
            config_clock_aligned_data_interval = int(value)
        elif key == "MeterValueSampleInterval":
            global meter_value_sample_interval
            meter_value_sample_interval = int(value)
        else:
            raise Exception("Unknown configuration change requested: ", key)
        
'''
# Function to create a single charge point, establish a WebSocket connection, and start several asynchronous tasks for it.
async def create_charge_point(i, base_url):
    cp_id = f"CP_{i}"  # Construct the charge point ID using the provided index.
    url = f"{base_url}/{cp_id}"  # Create the WebSocket URL using the base URL and charge point ID.
    # Establish a WebSocket connection to the server and create a charge point instance.
    async with websockets.connect(url, subprotocols=["ocpp2.0.1"]) as ws:  
        cp_instance = ChargePoint(cp_id, ws)  # Create a charge point instance with the ID and WebSocket.
        # Gather and run the following async tasks concurrently:
        await asyncio.gather(
            cp_instance.start(),  # Start the charge point, enabling it to handle incoming OCPP messages.
            cp_instance.send_boot_notification(),  # Send a boot notification to inform the server of the charge point's readiness.
            cp_instance.send_heartbeat(),  # Send a heartbeat message to maintain the WebSocket connection.
            cp_instance.periodic_meter_values(),  # Sends periodic meter values to the server.
            cp_instance.on_press()  # Start the key press listener to allow user interactions.
        )
    # Return the created charge point instance.
    return cp_instance



# Function to create multiple charge points and start them concurrently.
async def create_charge_points(num_charge_points, base_url):
    # Create a list of asynchronous tasks to create each charge point.
    tasks = [
        create_charge_point(i, base_url) for i in range(num_charge_points)
    ]
    # Execute all the charge point creation tasks concurrently and retrieve the created instances.
    charge_points = await asyncio.gather(*tasks)
    # Return the list of created charge point instances.
    return charge_points





#cs_ip, cs_port, cs_path, cp_name, *args
# Define the main asynchronous function, which will be the entry point of the program when it's run.
async def main():

    # Set the number of charge points to be created and communicated with.
    num_charge_points = 2

    # Define the base URL for WebSocket communication. 
    # 'ws' denotes the use of WebSocket protocol, 'localhost' is the domain (in this case, the local machine), 
    # and '9000' is the port on which the server (central system) is expected to be listening for connections.
    base_url = "ws://localhost:9000"  

    # Call the previously defined asynchronous function create_charge_points, 
    # passing the number of charge points to be created and the base URL for WebSocket communication.
    # This will initiate the creation of charge points and handle their communication with the central system.
    await create_charge_points(num_charge_points, base_url)  



if __name__ == '__main__':
    asyncio.run(main()) 
'''


async def create_charge_point(cp_id, base_url):
    url = f"{base_url}/{cp_id}"
    async with websockets.connect(url, subprotocols=["ocpp2.0.1"]) as ws:  
        cp_instance = ChargePoint(cp_id, ws)  
        print(f"Creating charge point: {cp_id}")


        keys = cp_keys[cp_id]
        start_key, stop_key = keys['start'], keys['stop']



        await asyncio.gather(
            cp_instance.start(),
            cp_instance.send_boot_notification(),
            cp_instance.charging_session(),
            cp_instance.send_heartbeat(),
            cp_instance.periodic_meter_values(),
            on_press(cp_instance, start_key, stop_key)
        )
    print("infinite loop hath terminated")
    return cp_instance

async def main(cp_id, base_url="ws://localhost:9000"):
    await create_charge_point(cp_id, base_url)

if __name__ == '__main__':
    import sys
    asyncio.run(main(sys.argv[1]))
