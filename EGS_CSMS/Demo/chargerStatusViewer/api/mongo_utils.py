from pymongo import MongoClient

class TransactionsDAL:
    def __init__(self, uri, dbName, collectionName):
        self.client = MongoClient(uri)
        self.db = self.client[dbName]
        self.collection = self.db[collectionName]

    def get_ongoing_transactions(self, charger_id):
        
        return list(self.collection.find({
            "chargerId": charger_id,
            "stopTime": None
        }))

    def get_finished_transactions(self, charger_id):

        return list(self.collection.find({
            "chargerId": charger_id,
            "stopTime": {"$exists": True, "$ne": None}
        })) 
        