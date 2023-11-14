import pymongo
from datetime import datetime

myclient = pymongo.MongoClient("mongodb://localhost:27017/")

db = myclient['OCPP_DB']

CP_db = db["CP's"]

transaction_db = db['Transactions']


def validate_CP_connection(requested_id):

    '''
    check if the CP attempting to connect exists in the database
    '''
    return CP_db.find_one({"_id":requested_id}) is not None

def update_CP_status(id, new_status):

    CP_db.update_one({"_id":id},{"$set":{"status":new_status}})

def get_cp_ids():
    cp_ids = CP_db.find({})
    return [cp["_id"] for cp in cp_ids]

def get_available_cps():
    available_cps = CP_db.find({"status":"available"})
    return [cp["_id"] for cp in available_cps]

def get_charging_cps():
    charging_cps = CP_db.find({"status":"charging"})
    return [cp["_id"] for cp in charging_cps]

def insert_transaction_in_db(transaction_id, CP_id):
    x = transaction_db.insert_one({
    "_id": transaction_id,
    "CP_ID": CP_id,
    "start_time": datetime.utcnow(),
    "end_time": None,
    "Energy_used": 0
})
    
def log_stop_transaction_in_db(transaction_id):
    transaction_db.update_one({"_id":transaction_id},{"$set":{"end_time":datetime.utcnow()}})



# mylist = [
#     {"_id":"CP_1",
#     "model": "Wallbox XYZ",   
#     "vendor_name": "anewone",   # charging station details
#     "serial_number":"123445",
#     "firmware_version":"1.2.3",
#     "CS_network_id": 1},
#     {"_id":"CP_2",
#     "model": "Wallbox XYZ",   
#     "vendor_name": "anewone",   # charging station details
#     "serial_number":"123445",
#     "firmware_version":"1.2.3",
#     "CS_network_id": 1},
#     {"_id":"CP_3",
#     "model": "Wallbox XYZ",   
#     "vendor_name": "anewone",   # charging station details
#     "serial_number":"123445",
#     "firmware_version":"1.2.3",
#     "CS,network_id":0},
#     {"_id":"CP_4",
#     "model": "Wallbox XYZ",   
#     "vendor_name": "anewone",   # charging station details
#     "serial_number":"123445",
#     "firmware_version":"1.2.3",
#     "CS_netowrk_id": 0}

# ]

# x = CP_db.insert_many(mylist)


# CP_db.update_many({},{"$set": {"status": "offline"}})



