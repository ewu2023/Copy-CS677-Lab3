from flask import Flask
from flask import request as FlaskRequest # Not to be confused with requests library
import requests
from Cache import LruCache

# For loading .env file
from dotenv import load_dotenv
import os
import sys

load_dotenv() # Load in environment variables from .env file

# Get catalog hostname and port from a environment variables
CATALOG_HOST = os.getenv('CATALOG_HOST')
CATALOG_PORT = int(os.getenv('CATALOG_PORT'))

# Option for caching
# 0 = do not cache lookups
# 1 = cache lookups
USE_CACHE = int(sys.argv[1])

# Get order server hostnames and ports from environment variables in .env
ORDER_SERVERS = {
    1: (os.getenv('ORDER_1_HOST'), int(os.getenv('ORDER_1_PORT'))),
    2: (os.getenv('ORDER_2_HOST'), int(os.getenv('ORDER_2_PORT'))),
    3: (os.getenv('ORDER_3_HOST'), int(os.getenv('ORDER_3_PORT')))
}

# Get the port assigned to the front end service
FRONT_PORT = int(os.getenv('FRONT_PORT'))

# Base URLs for catalog and order services
URL_CATALOG = f"http://{CATALOG_HOST}:{CATALOG_PORT}"

""" FLASK APP """
# Initialize in-memory cache
CACHE_SIZE = 3
cache = LruCache(CACHE_SIZE)

# Initialize flask app
app = Flask(__name__)

# Function to broadcast to the order replicas that the front end has chosen a leader
def send_leader_broadcast(leaderID):
    # Broadcast to order replicas that this server with id leaderID is the leader
    for serverID in ORDER_SERVERS:
        if serverID != leaderID:
            host, port = ORDER_SERVERS[serverID]
            url = f"http://{host}:{port}/leader-broadcast"
            attachedJSON = {"leader-id": leaderID}
            try:
                # Send message to the corresponding replica
                requests.post(url, json=attachedJSON)
            except:
                # If the replica was unresponsive, simply move on to next replica
                continue

# Ping command to ping order servers and select a leader
def ping_order_servers():
    pingLimit = 5
    pingOrder = [3, 2, 1] # Ping servers from highest to lowest ID
    numPings = 0
    
    # Attempt to ping the order servers until we reach the ping limit
    while numPings <= pingLimit:
        for id in pingOrder:
            host, port = ORDER_SERVERS[id]
            url = f"http://{host}:{port}/ping"
            # Attempt to make contact with the server
            try:
                res = requests.get(url)
                resJSON = res.json()
                if "success" in resJSON:
                    # Set the order service leader and return
                    leaderID = resJSON["success"]["server-id"]
                    global order_leader
                    order_leader = (host, port)

                    # Broadcast that a leader has been chosen
                    send_leader_broadcast(leaderID)
                    print(f"Found leader! Order Service {leaderID} at {order_leader}")
                    return True
                numPings += 1
            except:
                # Increment number of pings and continue
                numPings += 1
                continue
    
    # If we have reached the limit, return False: could not connect to order service
    return False

"""
Helper method for sending order requests to the order service

It will attempt to make a connection with the order service leader, and in the event
it cannot, it will run the ping_order_services function to determine a new leader
"""
def send_order_request(type: str, body, send_post=True, orderNum=-1):
    res = None
    while not res:
        # Attempt to connect with order service and get response
        try:   
            # Format the url to send an order request
            leaderHost, leaderPort = order_leader
            
            # Check if front end should send the GET or POST, based on whether /orders was called using GET or POST
            orderUrl = ''
            if send_post:
                orderUrl = f"http://{leaderHost}:{leaderPort}/{type}"
            else:
                orderUrl = f"http://{leaderHost}:{leaderPort}/lookup-order/{orderNum}"

            # Send GET or POST to the order service, depending on whether /orders was called using GET or POST
            res = None
            if send_post:
                res = requests.post(orderUrl, json=body)
            else:
                res = requests.get(orderUrl)

            # If the response came back as a 404, return it and its error message
            """
            Need this check because of how requests.Response is implemented
            requests.Response is "Truthy" if the status code of the response is between 200 and 400
            requests.Response is "Falsey" if the status code of the response is between 400 and 600
            """
            if res.status_code >= 400:
                return res
        except:
            # Case where response was not received due to a failure or timeout
            # Attempt to find a new leader
            leaderFound = ping_order_servers()
            if not leaderFound:
                # In the case where a leader could not be found, return None
                return None
    
    # Successfully got a response from order service
    # Return the response
    return res

""" Routes """
# GET /stocks/<stockName> route
# Allows user to look up a stock by name
@app.get('/stocks/<stockName>')
def fetch_stock(stockName):
    # Fetch stock from cache
    bodyJSON = cache.fetch(stockName)
    inCache = True # Flag signifying if the given stock is in the cache

    if not bodyJSON: # Case where stock was not in cache
        # Mark inCache flag as false
        inCache = False

        # If the specified stock is not in cache, query catalog
        url = f"{URL_CATALOG}/lookup/{stockName}"
        catalogRes = requests.get(url)

        # Parse the JSON from the response
        bodyJSON = catalogRes.json()
    
    # Format the response to the lookup request and return it
    if "error" in bodyJSON: # Case where lookup failed
        return bodyJSON, 404
    else:
        if not inCache and USE_CACHE: # Only put entries into the cache if the flag is set
            # If the stock information was not in the cache, insert it into the cache
            cache.insert(bodyJSON)
        
        fetchResponse = {
            "data": bodyJSON
        }
        return fetchResponse

# POST /orders route
# Allows user to trade shares of a stock
@app.post('/orders')
def handle_transaction():
    # Parse the JSON sent with the post request
    requestJSON = FlaskRequest.get_json()
    stockName = requestJSON["name"]
    quantity = requestJSON["quantity"]
    transactionType = requestJSON["type"]

    # Format the JSON to send to the order service
    orderJsonBody = {
        "name": stockName,
        "quantity": quantity
    }

    # Format the error message
    errorMsg = {
        "error": {
            "code": 500,
            "message": "could not trade stock"
        }
    }

    # Attempt to trade the stock
    orderRes = None
    if transactionType == 'sell': # Case where shares are being sold
        orderRes = send_order_request('sell', orderJsonBody)
    elif transactionType == 'buy': # Case where shares are being bought
        orderRes = send_order_request('buy', orderJsonBody)
    else: # Invalid transaction type
        return errorMsg, 500
    
    # Check response from order service for errors
    if orderRes.status_code == 404: # Case where a requested stock to trade could not be found
        # Return a 404 message stating the requested stock does not exist and can't be traded
        return {
            "error": {
                "code": 404,
                "message": "requested stock could not be traded because it could not be found"
            }
        }, 404
    elif orderRes.status_code >= 400: # Case where some failure or error occurred with the order service
        # Return a 500 message stating that the order service has failed
        return errorMsg, 500
    
    # Parse JSON from order response
    resJSON = orderRes.json()
    if "error" in resJSON:
        return errorMsg, 500
    else:
        return {"data": resJSON}

# Route for handling retrieving orders by order number
@app.get('/orders/<orderNum>')
def get_order(orderNum):
    # Send a lookup-order request to the lead order service
    orderRes = send_order_request(None, None, send_post=False, orderNum=orderNum)

    # Return message to client based on what the order service sent
    if orderRes.status_code == 404: # Case where order with orderNum could not be found
        # Return a 404 with the given message
        errMsg = f"could not find order with number {orderNum}"
        return {
            "error": {
                "code": 404,
                "message": errMsg
            }
        }, 404
    elif orderRes.status_code >= 400 or not orderRes: # Case where some other error occurred
        # Return a 500 with the given message
        errMsg = f"error occurred while retrieving order with number {orderNum}"
        return {
            "error": {
                "code": 500,
                "message": errMsg
            }
        }, 500
    else:
        # Request succeeded, so return the order
        orderJSON = orderRes.json()
        return {
            "data": {
                "number": orderNum,
                "name": orderJSON["name"],
                "quantity": orderJSON["quantity"],
                "type": orderJSON["type"]
            }
        }

# POST /invalidate/<stock_name> route
# Allows catalog service to inform front end of which stock to invalidate from the cache
@app.post('/invalidate/<stockName>')
def handle_invalidation(stockName):
    # Invalidate the given stock from the cache
    if cache.invalidate(stockName):
        # If the invalidation was successful, return a success message
        return {
            "success": {
                "code": 200,
                "message": "successfully removed stock"
            }
        }
    else:
        # If the stock was unable to be invalidated, return an error message
        # A stock may be unable to be invalidated if it isn't in the cache
        return {
            "error": {
                "code": 500,
                "message": "failed to remove stock"
            }
        }, 500

""" Routes for testing """
# Get the host and port of the leader replica
@app.get('/leader')
def get_leader():
    return {"leader-host": order_leader[0], "leader-port": order_leader[1]}

# Return the contents of the cache
@app.get('/dump-cache')
def dump_cache():
    return cache.cache
    
if __name__ == "__main__":
    # On startup, ping the order servers to determine a leader
    ping_order_servers()

    # By setting host to 0.0.0.0, allows app to run on all IP addresses associated with machine
    # Also assign the app to the port specified in the environment variables
    app.run(host='0.0.0.0', port=FRONT_PORT)