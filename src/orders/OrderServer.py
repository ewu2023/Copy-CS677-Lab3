import multiprocessing
from flask import Flask
from flask import request
import requests
import json
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

import sys
from dotenv import load_dotenv
import os

# Initialize maximum number of worker threads
MAX_THREADS = 32

# FOR TESTING
# Flag to determine if service should be shut down
shutdownFlag = False

# Load in environment variables
load_dotenv()

# Initialize host, port, and ID from environment variables or command line
ORDER_SERVERS = {
    1: (os.getenv('ORDER_1_HOST'), int(os.getenv('ORDER_1_PORT'))),
    2: (os.getenv('ORDER_2_HOST'), int(os.getenv('ORDER_2_PORT'))),
    3: (os.getenv('ORDER_3_HOST'), int(os.getenv('ORDER_3_PORT')))
}

SERVER_ID = int(sys.argv[1])
ORDER_HOST, ORDER_PORT = ORDER_SERVERS[SERVER_ID]

# TODO: Initialize catalog host and port from environment variable
CATALOG_HOST = os.getenv('CATALOG_HOST')
CATALOG_PORT = int(os.getenv('CATALOG_PORT'))

# Base URLs
URL_CATALOG = f"http://{CATALOG_HOST}:{CATALOG_PORT}"
URL_CATALOG_UPDATE = f"{URL_CATALOG}/update"
URL_CATALOG_LOOKUP = f"{URL_CATALOG}/lookup"

# Database lock
DB_LOCK = Lock()

# On-disk database file
DB_FILENAME = f"order{SERVER_ID}_database.json"

""" FLASK APP """
app = Flask(__name__)

def request_lookup(stockName):
    # Send a lookup request to the catalog
    url = f"{URL_CATALOG_LOOKUP}/{stockName}"
    lookupRes = requests.get(url)
    resJSON = lookupRes.json()

    # Return the response from the lookup
    return resJSON

def request_update(stockName, quantity, type):
    # Format JSON to send in update request
    updateJSON = {
        "name": stockName,
        "quantity": quantity,
        "type": type
    }

    # Send update request and return response
    updateRes = requests.post(URL_CATALOG_UPDATE, json=updateJSON)
    return updateRes.json()

# Helper method for broadcasting push messages
def broadcast_push(stockName, quantity, id, type):
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for replicaID in ORDER_SERVERS:
            if replicaID != leader_id:
                # Format push JSON
                pushJSON = {
                    "nextID": id,
                    "entry": {
                        "name": stockName,
                        "quantity": quantity,
                        "type": type
                    }
                }

                # Submit task to thread pool executor
                executor.submit(send_push, pushJSON, replicaID)

def send_push(bodyJson, replicaID):
    # Get the host and port of the replica to send the push request to
    replicaHost, replicaPort = ORDER_SERVERS[replicaID]

    # Format URL
    url = f"http://{replicaHost}:{replicaPort}/push"

    # Attempt to send push broadcast
    try:
        requests.post(url, json=bodyJson)
    except:
        # If a replica did not respond, simply exit
        return

# Helper function for synchronizing with other replicas
def synchronize():
    # Send a synchronize request to the other replicas
    DB_LOCK.acquire()
    for replicaID in ORDER_SERVERS:
        curHost, curPort = ORDER_SERVERS[replicaID]
        url = f"http://{curHost}:{curPort}/sync"

        try:
            # Read in database and get the ID for the next transaction
            memoryDB = read_database()
            nextID = memoryDB["nextID"]

            # Format JSON to send
            syncBody = {
                "lastID": nextID
            }

            # Attempt to send request to current replica
            syncRes = requests.get(url, json=syncBody)

            # Parse the json
            syncJSON = syncRes.json()
            curLeaderID = syncJSON["leader-id"]
            if curLeaderID > 0: # Case where a leader has already been chosen
                # Set the leader id, leader host, and leader port
                global leader_id
                leader_id = curLeaderID

                global leader_host, leader_port
                leader_host, leader_port = ORDER_SERVERS[leader_id]
                print(f"Leader: Replica #{curLeaderID} at {curHost}:{curPort}")
            
            # Get transactions since lastID
            missedTransactions = syncJSON["transactions"]
            for tid in missedTransactions:
                # Parse the information from the missed transaction
                curTransaction = missedTransactions[tid]
                name = curTransaction["name"]
                type = curTransaction["type"]
                quantity = curTransaction["quantity"]

                # Save the transaction to the database
                save_database(name, quantity, type, tid)
        except:
            continue

    DB_LOCK.release()


def read_database():
    # Read in database from disk
    memoryDB = {}
    with open(DB_FILENAME, 'r') as infile:
        memoryDB = json.load(infile)
    return memoryDB

def save_database(stockName, quantity, type, id):
    # Create ledger entry
    ledgerEntry = {
        "name": stockName,
        "quantity": quantity,
        "type": type
    }

    # Calculate next ID to use
    nextID = int(id) + 1

    # Read in current state of the database
    memoryDB = read_database()

    # Update and write out database to disk
    memoryDB["ledger"][id] = ledgerEntry
    memoryDB["nextID"] = nextID

    with open(DB_FILENAME, 'w') as outfile:
        outfile.write(json.dumps(memoryDB, indent=4))

""" Routes """
@app.post('/buy')
# Route for buying stocks
def handle_buy():
    # Parse information from request JSON
    reqJSON = request.get_json()
    stockName = reqJSON["name"]
    quantity = reqJSON["quantity"]

    # Request stock information from the catalog
    lookupJSON = request_lookup(stockName)

    # Check if an error occurred with the lookup
    if "error" in lookupJSON:
        # If an error occurred with the lookup, forward it to the front end
        errorObj = lookupJSON["error"]
        code = errorObj["code"]
        return lookupJSON, code
    
    """ Begin Critical Region """
    DB_LOCK.acquire()

    # Read next transaction id from database
    memoryDB = read_database()
    nextID = memoryDB["nextID"]
    
    # Format error and success messages
    errorMsg = {
        "error": {
            "code": 500,
            "message": "could not trade stock"
        }
    }

    successMsg = {
        "transaction-number": nextID
    }

    successFlag = False # Set flag if update is a success

    # Check if there are enough shares to sell
    remainingShares = lookupJSON["quantity"]

    if remainingShares >= quantity:
        # If there are enough shares to be bought, send update request
        updateResJSON = request_update(stockName, quantity, 'buy')
        if "success" in updateResJSON: # Case where update succeeds
            # Update database and return success message
            save_database(stockName, quantity, 'buy', nextID)
            successFlag = True
    
    # Release database lock
    DB_LOCK.release()
    """ End critical region """

    if successFlag:
        # If the trade was a success, broadcast push and return success
        broadcast_push(stockName, quantity, nextID, 'buy')
        return successMsg
    else:
        # Trade was not successful
        return errorMsg

@app.post('/sell')
def handle_sell():
    # Parse information from request
    reqJSON = request.get_json()
    stockName = reqJSON["name"]
    quantity = reqJSON["quantity"]

    # Send lookup request to catalog server
    lookupResJSON = request_lookup(stockName)

    # Check if there was an error when looking up the stock
    if "error" in lookupResJSON:
        # If there was an error with the lookup, return the error message and the code
        errorObj = lookupResJSON["error"]
        code = errorObj["code"]
        return lookupResJSON, code
    
    """ Begin critical region """
    # Acquire database lock
    DB_LOCK.acquire()

    # Read next transaction id from database
    memoryDB = read_database()
    nextID = memoryDB["nextID"]
    
    # Format error and success messages
    errMsg = {
        "error": {
            "code": 500,
            "message": "could not trade stock"
        }
    }

    successMsg = {
        "transaction-number": nextID
    }

    # If no error occurred, attempt update stock in catalog
    updateResJSON = request_update(stockName, quantity, 'sell')
    successFlag = False # Set this flag if the update was a success

    if "success" in updateResJSON: # If the update was a success, set the flag to true and update the database
        successFlag = True
        save_database(stockName, quantity, 'sell', nextID)
    
    # Release database lock
    DB_LOCK.release()
    """ End of critical region """

    # Determine which message to send
    if successFlag:
        # Transaction was successful, so send a success and send push messages
        broadcast_push(stockName, quantity, nextID, 'sell')
        return successMsg
    else:
        # Transaction was unsuccessful, so send an error
        return errMsg

# Route for handling order lookups by number
@app.get('/lookup-order/<orderNum>')
def handle_lookup_order(orderNum):
    # Search the database for the requested order number
    """ Begin critical section """
    DB_LOCK.acquire()
    memoryDB = read_database()
    ledger = memoryDB["ledger"]

    targetEntry = None
    if orderNum in ledger:
        # If the requested order number is in the ledger, set it as the target
        targetEntry = ledger[str(orderNum)]
    
    DB_LOCK.release()
    """ End critical section """

    # Return error or success message based on whether requested number was in ledger
    if targetEntry: # Case where order with requested number was found
        # Get the name, quantity, and type from the target entry
        name = targetEntry["name"]
        type = targetEntry["type"]
        quantity = targetEntry["quantity"]

        # Return message containing the information about the order
        return {
            "name": name,
            "type": type,
            "quantity": quantity
        }
    else: # Case where order with requested number was not found
        errMsg = f"could not find order with number {orderNum}"
        return {
            "error": {
                "code": 404,
                "message": errMsg
            }
        }, 404

# Ping route
# Allow front end to send ping messages to an order service replica
@app.get('/ping')
def handle_ping():
    # Front end will ping servers in order by their ID
    # So if an order service replica receives a ping, it becomes the leader
    global leader_host
    global leader_port
    leader_host, leader_port = ORDER_SERVERS[SERVER_ID]

    # Set ID of leader to this replica's ID
    global leader_id
    leader_id = SERVER_ID     

    return {
        "success": {
            "code": 200,
            "server-id": SERVER_ID,
            "message": "pong"
        }
    }

@app.post('/leader-broadcast')
def handle_leader_broadcast():
    # If the replica received a POST message on this route, a leader has been chosen
    # First, parse the request JSON to determine which server is the leader
    bodyJSON = request.get_json()

    global leader_id
    leader_id = bodyJSON["leader-id"]

    # Assign leader host, port based on provided ID
    global leader_host
    global leader_port
    leader_host, leader_port = ORDER_SERVERS[leader_id]

    # Return an acknowledgement
    return {
        "success": {
            "code": 200,
            "message": "acknowledge new leader"
        }
    }

# Route for handling push requests
# Whenever the leader makes an update, it will send a push message
# to each of the replicas to update their databases
@app.post('/push')
def handle_push():
    # Parse the entry to push into the database
    pushJSON = request.get_json()
    nextID = pushJSON["nextID"]
    ledgerEntry = pushJSON["entry"]

    # Acquire database lock
    DB_LOCK.acquire()

    # Read in current state
    memoryDB = read_database()

    # Add nextID and ledger entry to the database
    memoryDB["nextID"] = nextID + 1
    memoryDB["ledger"][nextID] = ledgerEntry

    # Save the database
    name = ledgerEntry["name"]
    quantity = ledgerEntry["quantity"]
    type = ledgerEntry["type"]
    save_database(name, quantity, type, nextID)
    
    # Release database lock
    DB_LOCK.release()

    # Return success message
    return {
        "success": {
            "code": 200,
            "message": "pushed entry to database"
        }
    }

@app.get('/sync')
def handle_sync():
    # Parse JSON from the sent request
    syncJSON = request.get_json()

    # Retrieve last known transaction ID from the request
    lastID = syncJSON["lastID"]

    """ Begin critical region """
    DB_LOCK.acquire()

    # Read in database from file
    memoryDB = read_database()
    
    # Get the ledger and the current transaction ID
    ledger = memoryDB["ledger"]
    nextID = memoryDB["nextID"]

    # Get each transaction that occurred since lastID
    curID = lastID
    transactions = {}
    while curID < nextID:
        transactions[str(curID)] = ledger[str(curID)]
        curID += 1
    
    """ End critical region """
    DB_LOCK.release()

    # Determine the leader
    curLeader = SERVER_ID
    try:
        # Get the globally stored leader id
        curLeader = leader_id
    except:
        # If the leader_id has not been initialized, set flag to -1
        curLeader = -1
    
    # Return a packet containing the current leader and transactions since lastID
    return {
        "leader-id": curLeader,
        "transactions": transactions
    }


# ROUTE FOR TESTING PURPOSES ONLY
# Terminates this replica of the order service
@app.post('/shutdown')
def terminate_early():
    # Send a message to the parent process to tell it to terminate this process
    PIPE.send(True)
    PIPE.close()
    return "Shutting down server..."

# Route for dumping contents of database
# Use for testing only
@app.get('/dump-database')
def dump_database():
    # Read in and return database
    memoryDB = read_database()
    return memoryDB

# Route for resetting contents of database
# Use for testing only
@app.post('/reset-database')
def reset_database():
    with open(DB_FILENAME, 'w') as outfile:
        # Re-formatted database
        reformattedDB = {
            "nextID": 0,
            "ledger": {}
        }

        outfile.write(json.dumps(reformattedDB, indent=4))
    
    # Return formatted database
    memoryDB = read_database()
    return memoryDB

def run_server(pipe: multiprocessing.Pipe):
    # Initialize a global pipe variable
    global PIPE
    PIPE = pipe

    # Attempt to synchronize with other order services first
    synchronize()

    # Start app
    app.run(host='0.0.0.0', port=ORDER_PORT)

if __name__ == "__main__":
    """ 
    Need to use a separate process for the Flask app because the library does not
    have a built-in shutdown function that can be called to terminate the server.
    The sys.exit() call does not seem to work either for this purpose.
    """

    # Create pipe to allow communication between main and server process
    parent_conn, child_conn = multiprocessing.Pipe()
    server_process = multiprocessing.Process(target=run_server, args=[child_conn])

    # Start server process
    server_process.start()
    if parent_conn.recv():
        print("Shutting down server.")
        server_process.terminate()