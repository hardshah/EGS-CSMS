from urllib import parse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Network, Item
from .mongo_utils import TransactionsDAL


uri = "mongodb+srv://hard:"+parse.quote_plus("titanic2")+"@egs.buswwxl.mongodb.net/?retryWrites=true&w=majority"
dbName = "transactions"
collection = "transactions"

# Network Views
class NetworkListView(ListView):
    model = Network
    context_object_name = 'networks'

class NetworkCreateView(CreateView):
    model = Network
    fields = ['location']
    success_url = reverse_lazy('network-list')

class NetworkUpdateView(UpdateView):
    model = Network
    fields = ['location']
    success_url = reverse_lazy('network-list')

class NetworkDeleteView(DeleteView):
    model = Network
    success_url = reverse_lazy('network-list')

# Charger Views
class ChargerListView(ListView):
    model = Item
    context_object_name = 'chargers'

class ChargerCreateView(CreateView):
    model = Item
    fields = ['network', 'charge_point_id']
    success_url = reverse_lazy('charger-list')

class ChargerUpdateView(UpdateView):
    model = Item
    fields = ['network', 'charge_point_id']
    success_url = reverse_lazy('charger-list')

class ChargerDeleteView(DeleteView):
    model = Item
    success_url = reverse_lazy('charger-list')

def View_Charger_Transactions(request, charger_id):
    transactionsDB = TransactionsDAL(uri, dbName, collection)
    # Fetching transactions using utility functions
    ongoing_transactions = transactionsDB.get_ongoing_transactions(charger_id)
    finished_transactions = transactionsDB.get_finished_transactions(charger_id)

    for transaction in ongoing_transactions:
    # Convert ObjectId to string and assign to a new key that doesn't start with an underscore
        transaction['transaction_id'] = str(transaction['_id'])
    
    for transaction in finished_transactions:
        transaction['transaction_id'] = str(transaction['_id'])
        transaction['usage'] = transaction['meterStop']-transaction['meterStart']
        transaction['duration'] = transaction['stopTime'] - transaction['startTime']

    context = {
        'ongoing_transactions': ongoing_transactions,
        'finished_transactions': finished_transactions,
        'charger_id': charger_id,
    }

    return render(request, 'transactions_view.html', context)