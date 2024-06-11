import requests
import random
import sys
import time
import json

def main():
    # Initialize list of stocks to search
    stockList = [
        'GameStart', 
        'FishCo', 
        'MenhirCo', 
        'BoarCo',
        'CrassusRealty',
        'AugustusPizza',
        'DivineComics',
        'LegionLogistics',
        'TiberAqueducts',
        'MercuryExpress'
    ]

    # Probability parameter
    p = float(sys.argv[1])

    # Number of repetitions
    n = int(sys.argv[2])

    # Get host and port
    host = sys.argv[3]
    port = int(sys.argv[4])

    # Get ID for this client session
    clientId = int(sys.argv[5]) # Set this to -1 if user does not want to record latencies

    # Begin a session
    ledger = {} # Maintain a ledger of all trades made over the course of the session
    lookupLatencies = [] # Store latency for lookup requests over session
    tradeLatencies = [] # Store latency for trade requests over session
    orderLookupLatencies = [] # Store latency for order lookup requests over session

    with requests.Session() as clientSession:
        # Initialize base URL from which all requests will send data to
        base_url = f"http://{host}:{port}"

        for i in range(n):
            # Print current request iteration
            print(f"-- REQUEST #{i} --")
            # Choose a random stock name
            index = random.randrange(0, len(stockList))
            stockName = stockList[index]

            # Send lookup request for stock
            lookupSendTime = time.perf_counter() # Record time before lookup

            lookupRes = clientSession.get(f"{base_url}/stocks/{stockName}")
            lookupData = (lookupRes.json())["data"]

            lookupRecvTime = time.perf_counter() # Record time after lookup

            # Compute latency in lookup and append to list
            lookupLatencies.append(lookupRecvTime - lookupSendTime)

            # Print result of lookup
            numShares = lookupData["quantity"]
            price = lookupData["price"]

            print(f"Stock Name: {stockName}\nPrice: {price}\nQuantity: {numShares}\n")

            # Check if the number of shares is > 0
            if numShares > 0:
                # If the number of shares > 0, decide if we want to trade
                rand_num = random.random()

                if rand_num < p: # Probability that a trade occurs
                    # Randomly choose quantity and type
                    quantity = random.randint(1, numShares + 1)
                    transactionType = 'buy' if random.random() < 0.5 else 'sell'

                    print(f"Attempting to {transactionType} {quantity} share(s) of {stockName}...")

                    # Write out JSON to send to server
                    payload = {
                        "name": stockName,
                        "quantity": quantity,
                        "type": transactionType
                    }

                    # Send JSON to request to trade stock
                    tradeSendTime = time.perf_counter() # Record time trade request was sent

                    tradeRes = clientSession.post(f"{base_url}/orders", json=payload)
                    tradeStatus = tradeRes.json()

                    tradeRecvTime = time.perf_counter() # Record time trade request was received

                    # Compute latency in trade request and append to list
                    tradeLatencies.append(tradeRecvTime - tradeSendTime)

                    if "error" in tradeStatus:
                        errorInfo = tradeStatus["error"]
                        errCode = errorInfo["code"]
                        errMsg = errorInfo["message"]
                        print(f"Error occurred.\nCode: {errCode}\nMessage from Server: {errMsg}\n")
                    else:
                        tradeData = tradeStatus["data"]
                        transactionNum = tradeData["transaction-number"]
                        print(f"Transaction Success! Transaction #: {transactionNum}\n")

                        # Add this transaction to the ledger
                        ledger[transactionNum] = payload
            """ End for loop """

        # Validate each transaction by sending GET /orders requests
        for tid in ledger:
            # Format the GET request URL
            getUrl = f"{base_url}/orders/{tid}"

            # Await for response from front end
            t_sendOrderLook = time.perf_counter() # Mark time the request was sent

            frontRes = requests.get(getUrl)
            dataJson = frontRes.json()

            t_recvOrderLook = time.perf_counter() # Mark time the request was received
            orderLookupLatencies.append(t_recvOrderLook - t_sendOrderLook) # Add latency of order lookup to list

            dataObj = dataJson["data"]

            # Validate that the transactions sent by the server match the local ledger
            receivedEntry = {
                "name": dataObj["name"],
                "quantity": dataObj["quantity"],
                "type": dataObj["type"]
            }

            recordedEntry = ledger[tid]

            try:
                # Assert that transaction ids match
                assert(int(dataObj["number"]) == tid)

                # Assert that the ledger entries match
                assert(receivedEntry["name"] == recordedEntry["name"])
                assert(receivedEntry["quantity"] == recordedEntry["quantity"])
                assert(receivedEntry["type"] == recordedEntry["type"])
                print(f"Transaction #{tid} confirmed.")
            except Exception as e:
                print("-- ERROR: Entries do not match! --")
                print(f"Local copy: {recordedEntry}")
                print(f"Server copy: {receivedEntry}\n")
                continue
        
        # Write out latencies to a json file
        if clientId >= 0:
            with open(f"Client_{clientId}_data.json", 'w') as outfile:
                data = {
                    "lookup-data": lookupLatencies,
                    "trade-data": tradeLatencies,
                    "order-look-data": orderLookupLatencies
                }

                outfile.write(json.dumps(data, indent=4))

if __name__ == "__main__":
    main()

                