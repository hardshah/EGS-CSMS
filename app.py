from fastapi import FastAPI, Request, Depends, HTTPException, status, WebSocket, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import central_system as cs
import websockets
from starlette.websockets import WebSocketDisconnect
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from DB.db import CP_db, transaction_db

logging.basicConfig(level=logging.INFO)

ws_location_filters = {}

app = FastAPI()
templates = Jinja2Templates(directory='templates')
app.mount("/static",StaticFiles(directory='static'), name='static')

@app.get("/",response_class=HTMLResponse)
async def get_metrics(request: Request, location: Optional[str] = None):
    query = {}
    if location:
        query['CS_network_id'] = location
    else:
        location = ''
    cps = list(CP_db.find(query))
    return templates.TemplateResponse("index.html", {"request":request ,"cps":cps, "selected_location": location})

@app.post("/add-chargepoint")
async def add_chargepoint(request: Request, cp_id: str=Form(...), location:str=Form(...), model:str=Form(...), vendor_name:str=Form(...),serial_number:str=Form(...),firmware_version:str=Form(...)):
    # Create the document to insert
    chargepoint_document = {
        "_id": cp_id,
        "model": model,
        "vendor_name": vendor_name,
        "serial_number": serial_number,
        "firmware_version": firmware_version,
        "CS_network_id": location,
        "status":"offline"
    }
    # Insert the document inot the database
    CP_db.insert_one(chargepoint_document)
    # Redirect back to the page with the form
    return RedirectResponse(url='/',status_code=303)

@app.get("/locations", response_class=HTMLResponse)
async def get_locations(request: Request):
    locations = CP_db.distinct("CS_network_id")
    return templates.TemplateResponse("locations.html", {"request":request, "locations":locations})


@app.get("/metrics/{cp_id}", response_class=HTMLResponse)
async def get_charge_point_metrics(request: Request, cp_id: str):
    logging.info(f"Invoked get_charge_point_metrics for CP {cp_id}")
    cp_data = cs.meter_values_store.get(cp_id, {})
    logs = cs.chargepoint_logs.get(cp_id, [])

    if not isinstance(cp_data, dict):
        cp_data = {}
    return templates.TemplateResponse(
        "charge_point_metrics.html",
        {"request": request, "cp_id":  cp_id, "cp_data":cp_data, "logs": logs}
    )

@app.get("/transactions", response_class=HTMLResponse)
async def get_transactions(request: Request,cp_id:str=None, date:str=None):
    query = {}
    if cp_id:
        query['CP_ID'] = cp_id
    if date:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        next_day = date_obj + timedelta(days=1)
        query['start_time'] = {'$gte': date_obj, '$lt': next_day}

    transactions = list(transaction_db.find(query).sort('start_time', -1))
    # Format dates for display
    for transaction in transactions:
        transaction['_id'] = str(transaction['_id'])
        transaction['start_time'] = transaction['start_time'].strftime('%Y-%m-%d %H:%M:%S')
        if transaction.get('end_time'):
            transaction['end_time'] = transaction['end_time'].strftime('%Y-%m-%d %H:%M:%S')
    return templates.TemplateResponse("transactions.html", {"request": request, "transactions": transactions })


@app.websocket("/ws/{cp_id}")
async def websocket_endpoint(websocket: WebSocket, cp_id: str):
    await websocket.accept()
    while True:
        cp_data = cs.meter_values_store.get(cp_id, {})
        logs = cs.chargepoint_logs.get(cp_id, [])

        data = {
            'type': 'update',
            'cp_data': cp_data,
            'logs': logs
        }

        await websocket.send_json(data)
        await asyncio.sleep(1)

@app.websocket("/cp-status-updates")
async def cp_status_updates(websocket: WebSocket):
    await websocket.accept()
    ws_id = id(websocket)

    ws_location_filters[ws_id] = {}
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(),timeout=1.0)
              

                if 'location' in data:
                    ws_location_filters[ws_id]['CS_network_id'] = data['location']

       
            except asyncio.TimeoutError:
                pass

            filter_query = ws_location_filters[ws_id]
            cps_in_db = list(CP_db.find(filter_query, {"_id": 1, "status": 1}))

            await websocket.send_json({
                'type': 'cp_status_update',
                'cps_in_db':cps_in_db
            })
            await asyncio.sleep(1)
    
    except WebSocketDisconnect:
        ws_location_filters.pop(ws_id, None)
    except Exception as e:
        ws_location_filters.pop(ws_id, None)
        print(f"An error occurred: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cs.start_websocket_server())
