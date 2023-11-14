import datetime
import random

POWERCAPACITY = 45000

def get_demand():

    hour = datetime.datetime.now().hour
    month = datetime.datetime.now().month

    base_demand = 5000


    if 9 <= hour <= 19:
        daytime_demand = random.randint(25000, 35000)
    else:
        daytime_demand = random.randint(5000, 15000)


    if month in [6,7,8,12,1,2]:
        seasonal_demand = random.randint(30000,40000)
    else:
        seasonal_demand = random.randint(15000, 25000)

    total_demand = (daytime_demand + seasonal_demand) / 2

    total_demand = min(POWERCAPACITY, total_demand)

    return total_demand

print(get_demand())
