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


class ChargePoint(cp):
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
                # Heartbeat rate in sec
                await asyncio.sleep(int(config_heartbeat_interval))
            except:
                raise

    async def send_authorize(self):     # sending the request has not been implemented
        request = call.AuthorizePayload(
            id_tag='abcdefghijklmnopqrst'
        )

    async def periodic_meter_values(self):
        global config_clock_aligned_data_interval
        while True:
            try:
                response = await self.send_meter_values()
                await asyncio.sleep(int(config_clock_aligned_data_interval))
            except:
                raise


    async def send_transaction_event(self):
        request = call.TransactionEventPayload(
            event_type="Started",
            timestamp=datetime.utcnow().isoformat(),
            trigger_reason="Authorized",  # Assumes the user has already been authenticated
            seq_no=1, # Incremental sequence number, helps with determining if all messages of a transaction have been recieved.
            transaction_info={
                "transaction_id": "123ABC",
                "charging_state":"Charging"
            }
        )
        await self.call(request)
        logging.info("Transaction Event request was sent!")
        

        
    @on("RequestStartTransaction") 
    async def on_start_transaction(self, id_token, **kwargs ):
        logging.info("start Transaction received: %s", id_token)

        # await self.send_status_notification(ChargePointErrorCode.ev_communication_error, ChargePointStatus.preparing)
        
        global meter_value_power_active_import
        global meter_value_voltage_L1
        global meter_value_voltage_L2
        global meter_value_voltage_L3
        global meter_value_energy_active_import_register
        global meter_value_power_offered
        # global meter_value_temperature
        global meter_value_soc

        meter_value_power_active_import.value = charging_meter_value_power_active_import_value
        meter_value_voltage_L1.value = charging_meter_value_voltage_L1
        meter_value_voltage_L2.value = charging_meter_value_voltage_L2
        meter_value_voltage_L3.value = charging_meter_value_voltage_L3
        meter_value_energy_active_import_register.value = charging_meter_value_energy_active_import_register_value
        meter_value_power_offered.value = charging_meter_value_power_offered_value
        # meter_value_temperature.value = charging_meter_value_temperature_value
        meter_value_soc.value = charging_meter_value_soc_value

        return call_result.RequestStartTransactionPayload(
            status = "Accepted",
            transaction_id= id_token['id_token']
        )

    async def stop_transaction(self, transaction_id):
        request = call.StopTransactionPayload(
            transaction_id=transaction_id,
            meter_stop=1,          # Initial Energy meter value / integer
            timestamp=datetime.utcnow().isoformat()
        )
        response = await self.call(request)
        await self.send_status_notification(ChargePointErrorCode.high_temperature, ChargePointStatus.finishing)
        global meter_value_power_active_import
        global meter_value_voltage_L1
        global meter_value_voltage_L2
        global meter_value_voltage_L3
        global meter_value_energy_active_import_register
        global meter_value_power_offered
        global meter_value_temperature
        global meter_value_soc

        meter_value_power_active_import.value = stopped_meter_value_power_active_import_value
        meter_value_voltage_L1.value = stopped_meter_value_voltage_L1
        meter_value_voltage_L2.value = stopped_meter_value_voltage_L2
        meter_value_voltage_L3.value = stopped_meter_value_voltage_L3
        meter_value_energy_active_import_register.value = stopped_meter_value_energy_active_import_register_value
        meter_value_power_offered.value = stopped_meter_value_power_offered_value
        meter_value_temperature.value = stopped_meter_value_temperature_value
        meter_value_soc.value = stopped_meter_value_soc_value

        if response.id_tag_info["status"] == "Accepted":
            logging.info("Charging stopped.")
        else:
            logging.error("Error in executing StopTransaction!")
        await self.send_status_notification(ChargePointErrorCode.no_error, ChargePointStatus.available)

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

    async def send_meter_values(self):
        request = call.MeterValuesPayload(
            evse_id=1,
            meter_value=[
                MeterValue(
                    timestamp=datetime.utcnow().isoformat(),
                    sampled_value=[
                        meter_value_power_active_import,
                        meter_value_voltage_L1,
                        meter_value_voltage_L2,
                        meter_value_voltage_L3,
                        meter_value_energy_active_import_register,
                        meter_value_power_offered,
                        # meter_value_temperature,
                        meter_value_soc]
                )
            ]
        )
        response = await self.call(request)

    @on(Action.SetChargingProfile)       # sets charging profile, very important for smart charging
    async def set_charging_profile(self, connector_id, cs_charging_profiles):
        global meter_value_power_active_import
        global last_known_power_limit
        global scheduler
        unit = cs_charging_profiles["charging_schedule"]["charging_rate_unit"]
        limit = cs_charging_profiles["charging_schedule"]["charging_schedule_period"][0]["limit"]
        duration = cs_charging_profiles["charging_schedule"]["duration"]

        if float(meter_value_power_active_import.value) > 0:
            if unit == "W" and limit:
                last_known_power_limit = meter_value_power_active_import.value
                meter_value_power_active_import.value = f'{limit}'
            elif unit == "A" and limit:
                limit = decimal.Decimal(float(meter_value_voltage_L1.value))*limit
                last_known_power_limit = meter_value_power_active_import.value
                meter_value_power_active_import.value = f'{limit}'
            else:
                return call_result.SetChargingProfilePayload(
                    status=ChargingProfileStatus.rejected
                )
            scheduler = AsyncIOScheduler()
            scheduler.add_job(restore_from_limit_power, 'date',
                              run_date=datetime.now()+timedelta(seconds=duration))
            scheduler.start()
            return call_result.SetChargingProfilePayload(
                status=ChargingProfileStatus.accepted
            )
        else:
            return call_result.SetChargingProfilePayload(
                status=ChargingProfileStatus.rejected
            )

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
        
async def on_press(cp):
    while True:
        if keyboard.is_pressed('p'):
            await cp.send_transaction_event()
            await asyncio.sleep(0.5)
        await asyncio.sleep(0.1)


#cs_ip, cs_port, cs_path, cp_name, *args
async def main():
    # global CP_VENDOR
    # if len(args) > 0:
    #     CP_VENDOR = args[0]
    async with websockets.connect(
        # 'ws://' + cs_ip + ':' + cs_port + cs_path + cp_name,
        # subprotocols=['ocpp2.0.1']
        "ws://localhost:9000/CP_1", subprotocols=["ocpp2.0.1"]
    ) as ws:

        # cp = ChargePoint(cp_name, ws)
        cp = ChargePoint("CP_1", ws)
        
        await asyncio.gather(
            cp.start(), 
            cp.send_boot_notification(), 
            cp.send_heartbeat(), 
            cp.periodic_meter_values(), 
            on_press(cp))

if __name__ == '__main__':
    # if(len(sys.argv) == 5):
    #     asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))
    # elif (len(sys.argv) == 6):
    #     asyncio.run(main(sys.argv[1], sys.argv[2],
    #                 sys.argv[3], sys.argv[4], sys.argv[5]))
    # else:
    #     print("Incorrect number of arguments supplied. Expected 4: CS_IP, CS_PORT, CS_PATH, CP_NAME, CP_VENDOR(optional)")
    asyncio.run(main()) 