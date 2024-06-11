import requests
import os
from dotenv import load_dotenv

# This test assumes the cache size in the front end is 3

# Load in environment variables
load_dotenv()

# Initialize global vars
FRONT_HOST = os.getenv('FRONT_HOST')
FRONT_PORT = int(os.getenv('FRONT_PORT'))

ORDER_SERVERS = {
    1: (os.getenv('ORDER_1_HOST'), int(os.getenv('ORDER_1_PORT'))),
    2: (os.getenv('ORDER_2_HOST'), int(os.getenv('ORDER_2_PORT'))),
    3: (os.getenv('ORDER_3_HOST'), int(os.getenv('ORDER_3_PORT')))
}

# Initialize URLs to front end endpoints
URL_BASE = f"http://{FRONT_HOST}:{FRONT_PORT}"
URL_LOOKUP = f"{URL_BASE}/stocks"
URL_ORDERS = f"{URL_BASE}/orders"
URL_CACHE = f"{URL_BASE}/dump-cache"

# Set valid and invalid stock options
VALID_STOCK_OPTION_1 = "GameStart" # Lookup this one
VALID_STOCK_OPTION_2 = "FishCo" # Trade this one
VALID_STOCK_OPTION_3 = "CrassusRealty"
VALID_STOCK_OPTION_4 = "MenhirCo"
INVALID_STOCK_OPTION = "Pear"

# Test if front end returns correct response to valid lookup
def test_valid_lookup():
    # Send lookup request
    url = f"{URL_LOOKUP}/{VALID_STOCK_OPTION_1}"
    lookupRes = requests.get(url)
    print(lookupRes)
    lookupJSON = lookupRes.json()

    try:
        # Assert that the front end did not return an error
        assert("error" not in lookupJSON)
        assert("data" in lookupJSON)

        # Assert that the correct stock was returned
        dataObj = lookupJSON["data"]
        assert(dataObj["name"] == VALID_STOCK_OPTION_1)
        assert(dataObj["price"] == 15.99)
        assert(dataObj["quantity"] == 100)

        print("Passed test_valid_lookup")
        print(f"Message received: {lookupJSON}\n")
        return (True, "test_valid_lookup")
    except:
        print("Failed test_valid_lookup")
        print(f"Message received: {lookupJSON}\n")
        return (False, "test_valid_lookup")

# Test if front end returns correct response to invalid lookup
def test_invalid_lookup():
    # Send lookup request
    url = f"{URL_LOOKUP}/{INVALID_STOCK_OPTION}"
    lookupRes = requests.get(url)
    lookupJSON = lookupRes.json()

    # Set expected message
    expectedMsg = {
        "error": {
            "code": 404,
            "message": "stock not found"
        }
    }

    try:
        # Assert that an error was returned by the front end
        assert("error" in lookupJSON)

        # Parse error object and assert that the correct code was returned
        errorObj = lookupJSON["error"]
        assert(errorObj["code"] == 404)

        print("Passed test_invalid_lookup")
        print(f"Message received: {lookupJSON}\n")
        return (True, "test_invalid_lookup")
    except:
        print("Failed test_invalid_lookup")
        print(f"Message received: {lookupJSON}")
        print(f"Expected message: {expectedMsg}\n")
        return (False, "test_invalid_lookup")

# Test buying a stock from the front end
def test_frontend_buy():
    # Format the JSON to send to front end
    buyReqJSON = {
        "name": VALID_STOCK_OPTION_2,
        "quantity": 10,
        "type": "buy"
    }

    # Send lookup request for same stock first. This will be used to compare
    lookupUrl = f"{URL_LOOKUP}/{VALID_STOCK_OPTION_2}"
    lookupRes = requests.get(lookupUrl)
    lookupJSON = lookupRes.json()

    # Send buy request
    buyRes = requests.post(URL_ORDERS, json=buyReqJSON)
    buyResJSON = buyRes.json()

    # Send another lookup request for the same stock after the buy
    lookupRes2 = requests.get(lookupUrl)
    lookupJSON_2 = lookupRes2.json()

    try:
        # Assert that the requests did not return errors
        assert("error" not in lookupJSON and "error" not in buyResJSON)
        assert("error" not in lookupJSON_2)

        # Assert that a transaction number was returned
        buyResData = buyResJSON["data"]
        assert("transaction-number" in buyResData)

        # Compare the number of shares before and after the buy
        beforeBuy = lookupJSON["data"]["quantity"]
        afterBuy = lookupJSON_2["data"]["quantity"]

        assert(beforeBuy > afterBuy)
        assert(beforeBuy == (afterBuy + 10))

        print("Passed test_frontend_buy")
        print(f"Message before buying shares: {lookupJSON}")
        print(f"Message after buying shares: {lookupJSON_2}\n")
        return(True, 'test_frontend_buy')
    except:
        print("Failed test_frontend_buy")
        print(f"Message before buying shares: {lookupJSON}")
        print(f"Message after buying shares: {lookupJSON_2}")
        print(f"Received response for buy: {buyResJSON}\n")
        return (False, 'test_frontend_buy')

# Test selling a stock from the front end
def test_frontend_sell():
    # Format JSON to send to front end sell endpoint
    sellJSON = {
        "name": VALID_STOCK_OPTION_2,
        "quantity": 10,
        "type": "sell"
    }

    # Send a lookup request for the stock first
    lookupUrl = f"{URL_LOOKUP}/{VALID_STOCK_OPTION_2}"
    lookupRes_1 = requests.get(lookupUrl)
    lookupJSON_1 = lookupRes_1.json()

    # Sell the stock
    sellRes = requests.post(URL_ORDERS, json=sellJSON)
    sellJSON = sellRes.json()

    # Send lookup request for the stock after selling it
    lookupRes_2 = requests.get(lookupUrl)
    lookupJSON_2 = lookupRes_2.json()

    try:
        # Assert that no requests returned an error
        assert("error" not in lookupJSON_1)
        assert("error" not in lookupJSON_2)
        assert("error" not in sellJSON)

        # Assert that the transaction was conducted correctly
        lookupData1 = lookupJSON_1["data"]
        lookupData2 = lookupJSON_2["data"]

        beforeSell = lookupData1["quantity"]
        afterSell = lookupData2["quantity"]

        assert(beforeSell < afterSell)
        assert(afterSell == (beforeSell + 10))

        print("Passed test_frontend_sell")
        print(f"Message before selling shares: {lookupJSON_1}")
        print(f"Message after selling shares: {lookupJSON_2}\n")
        return (True, 'test_frontend_sell')
    except:
        print("Failed test_frontend_sell")
        print(f"Message received from front end: {sellJSON}\n")
        return (False, 'test_frontend_sell')

# Test trading an invalid stock
def test_trade_invalid_stock():
    # Format JSON to send to endpoint
    buyReqJSON = {
        "name": INVALID_STOCK_OPTION,
        "quantity": 10,
        "type": "buy"
    }

    sellReqJSON = {
        "name": INVALID_STOCK_OPTION,
        "quantity": 10,
        "type": "sell"
    }

    # Send buy and sell request for the same invalid stock
    buyResJSON = (requests.post(URL_ORDERS, json=buyReqJSON)).json()
    sellResJSON = (requests.post(URL_ORDERS, json=sellReqJSON)).json()

    try:
        # Assert that both requests returned errors
        assert("error" in buyResJSON and "error" in sellResJSON)

        # Assert that both requests returned 404 errors: the stocks they requested to trade do not exist
        buyErr = buyResJSON["error"]
        sellErr = sellResJSON["error"]
        
        assert(buyErr["code"] == 404)
        assert(sellErr["code"] == 404)

        print("Passed test_trade_invalid_stock")
        print(f"Message received from buy request: {buyResJSON}")
        print(f"Message received from sell request: {sellResJSON}\n")
        return (True, 'test_trade_invalid_stock')
    except:
        print("Failed test_trade_invalid_stock")
        print(f"Message received from buy request: {buyResJSON}")
        print(f"Message received from sell request: {sellResJSON}\n")
        return (False, 'test_trade_invalid_stock')

# Test retrieving a valid order with a valid ID
def test_get_valid_order():
    # Send GET /orders request to front end service
    orderNum = 0 # Get order with number 0
    getOrderUrl = f"{URL_ORDERS}/{orderNum}"
    orderRes = requests.get(getOrderUrl)
    orderJSON = orderRes.json()

    try:
        # Assert that the front end did not return an error
        assert("error" not in orderJSON)

        # Parse the data object sent with the response
        resData = orderJSON["data"]

        # Assert that the correct order was returned
        assert(resData["number"] == orderNum)

        print("Passed test_get_valid_order")
        print(f"Received message: {orderJSON}")
        return (True, 'test_get_valid_order')
    except:
        print("Failed test_get_valid_order")
        print(f"Received message: {orderJSON}")
        return (False, 'test_get_valid_order')

# Test retrieving an invalid order with an invalid ID
def test_get_invalid_order():
    # Send GET /orders request to front end
    orderNum = 999999999
    getOrderUrl = f"{URL_ORDERS}/{orderNum}"
    orderRes = requests.get(getOrderUrl)
    orderJSON = orderRes.json()

    try:
        # Assert that the front end returned a 404 error
        assert("error" in orderJSON)

        errorObj = orderJSON["error"]
        assert(errorObj["code"] == 404)

        print("Passed test_get_invalid_order")
        print(f"Received message: {orderJSON}")
        return (True, 'test_get_invalid_order')
    except:
        print("Failed test_get_invalid_order")
        print(f"Received message: {orderJSON}")
        return (False, 'test_get_invalid_order')

# Test the LRU policy of the front end cache
def test_lru_cache():
    print("BEGIN: test_lru_cache")
    # For this test, the size of the LRU cache at the front end was configured to 3
    # Initialize GET /stocks/<stockName> URLs
    url1 = f"{URL_LOOKUP}/{VALID_STOCK_OPTION_1}"
    url2 = f"{URL_LOOKUP}/{VALID_STOCK_OPTION_2}"
    url3 = f"{URL_LOOKUP}/{VALID_STOCK_OPTION_3}"
    url4 = f"{URL_LOOKUP}/{VALID_STOCK_OPTION_4}"

    urls = [
        url1,
        url2,
        url3,
        url4
    ]

    # Send requests using first 3 urls
    for i in range(3):
        curUrl = urls[i]
        print(f"URL: {curUrl}")
        print(f"Response: {(requests.get(curUrl)).json()}\n")
    
    # First test: Assert that cache has length 3
    try:
        # Retrieve cache from front end
        cache = (requests.get(URL_CACHE)).json()
        assert(len(cache) == 3) # Since at least 3 requests were issued, make sure cache is full
        print("Cache has expected length of 3")
    except:
        print("Failed test_lru_cache")
        print(f"Length of cache: {len(cache)}")
        print(f"Expected cache length of 3\n")
        return (False, 'test_lru_cache')
    
    # Second test: Assert that all entries are in appropriate place in cache when retrieving cached entries
    try:
        # Issue a request for url1
        requests.get(url1)

        # Retrieve the cache
        cache = (requests.get(URL_CACHE)).json()

        # Assert that VALID_STOCK_OPTION_1 is at the back
        mostRecentEntry = cache[len(cache) - 1]
        assert(mostRecentEntry["name"] == VALID_STOCK_OPTION_1)

        # Assert that VALID_STOCK_OPTION_2 is at the front
        oldestEntry = cache[0]
        assert(oldestEntry["name"] == VALID_STOCK_OPTION_2)

        # Assert that VALID_STOCK_OPTION_3 is in the middle
        middleEntry = cache[1]
        assert(middleEntry["name"] == VALID_STOCK_OPTION_3)

        print("Cache has expected structure after retrieving old entry")
    except:
        # Format expected and received order objects
        expectedOrdering = [VALID_STOCK_OPTION_2, VALID_STOCK_OPTION_3, VALID_STOCK_OPTION_1]
        receivedOrder = []
        for entry in cache:
            receivedOrder.append(entry["name"])
        
        print("Failed test_lru_cache")
        print("Cache did not have expected structure")
        print(f"Expected order: {expectedOrdering}")
        print(f"Received order: {receivedOrder}\n")
        return(False, 'test_lru_cache')

    # Third test: Assert that cache evicts the correct stock
    try:
        # Issue a request for VALID_STOCK_OPTION_4
        requests.get(url4)

        # Retrieve the cache
        cache = (requests.get(URL_CACHE)).json()

        # Assert that VALID_STOCK_OPTION_4 is at the end
        lastEntry = cache[len(cache) - 1]
        assert(lastEntry["name"] == VALID_STOCK_OPTION_4)

        # Assert that options 3 and 1 are in correct position
        firstEntry = cache[0]
        secondEntry = cache[1]
        assert(firstEntry["name"] == VALID_STOCK_OPTION_3)
        assert(secondEntry["name"] == VALID_STOCK_OPTION_1)

        print("Correct stock was evicted after a new stock was retrieved from catalog")
    except:
        # Format expected and received order objects
        expectedOrdering = [VALID_STOCK_OPTION_3, VALID_STOCK_OPTION_1, VALID_STOCK_OPTION_4]
        receivedOrder = []
        for entry in cache:
            receivedOrder.append(entry["name"])

        print("Failed test_lru_cache")
        print("Correct stock was not evicted, or there was some error with the structure.")
        print(f"Expected Order: {expectedOrdering}")
        print(f"Received Order: {receivedOrder}\n")
        return (False, 'test_lru_cache')
    
    # Passed all cache-related tests
    print("PASSED: TEST_LRU_CACHE\n")
    return (True, 'test_lru_cache')

# Test that entries in the front end's cache are correctly invalidated
def test_invalidate():
    # Lookup 3 valid stocks to set state of the cache to something verifiable
    print("BEGIN: test_invalidate")
    lookupUrl0 = f"{URL_LOOKUP}/{VALID_STOCK_OPTION_2}"
    lookupUrl1 = f"{URL_LOOKUP}/{VALID_STOCK_OPTION_3}"
    lookupUrl2 = f"{URL_LOOKUP}/{VALID_STOCK_OPTION_4}"

    print(f"URL: {lookupUrl0}")
    print(f"Response: {(requests.get(lookupUrl0)).json()}")

    print(f"URL: {lookupUrl1}")
    print(f"Response: {(requests.get(lookupUrl1)).json()}\n")

    print(f"URL: {lookupUrl2}")
    print(f"Response: {(requests.get(lookupUrl2)).json()}\n")

    # Fetch the cache before the invalidation
    cacheBefore = (requests.get(URL_CACHE)).json()

    # Invalidate stocks by sending a sell and a buy request
    sellJson = {
        "name": VALID_STOCK_OPTION_3,
        "quantity": 10,
        "type": "sell"
    }
    sellResJson = (requests.post(URL_ORDERS, json=sellJson)).json()
    print(f"Sell Response: {sellResJson}")

    buyJson = {
        "name": VALID_STOCK_OPTION_4,
        "quantity": 10,
        "type": "sell"
    }
    buyResJson = (requests.post(URL_ORDERS, json=buyJson)).json()
    print(f"Buy Response: {buyResJson}\n")

    # Get state of cache after each transaction
    cacheAfter = (requests.get(URL_CACHE)).json()

    # Assert that stocks were removed from cache
    expectedCache = [VALID_STOCK_OPTION_2]
    try:
        # Since two stocks should have been invalidated, assert that length = 1
        assert(len(cacheAfter) == 1)

        # Assert that the stocks were in the cache before the transaction
        assert(cacheBefore[1]["name"] == VALID_STOCK_OPTION_3)
        assert(cacheBefore[2]["name"] == VALID_STOCK_OPTION_4)

        # Assert that the stock in the cache is neither option 3 or 4
        assert(cacheAfter[0]["name"] == VALID_STOCK_OPTION_2)
        assert(cacheAfter[0]["name"] != VALID_STOCK_OPTION_3)
        assert(cacheAfter[0]["name"] != VALID_STOCK_OPTION_4)

        outputCache = [cacheAfter[0]["name"]]
        print(f"Stocks successfully invalidated: {VALID_STOCK_OPTION_3, VALID_STOCK_OPTION_4}")
        print(f"State of cache: {outputCache}\n")
    except:
        receivedCache = []
        for entry in cacheAfter:
            receivedCache.append(entry["name"])
        
        print("Stocks not successfully invalidated.")
        print(f"Expected state: {expectedCache}")
        print(f"Received state: {receivedCache}")
        print("Failed test_invalidate")
        return (False, 'test_invalidate')

    # Passed test
    print("PASSED: test_invalidate")
    return (True, 'test_invalidate')

# Test consistency among the local databases for each order service
def test_consistency():
    print("BEGIN: test_consistency")
    # First, send a buy request
    # Purchase 10 shares of VALID_STOCK_OPTION_2
    buyJson = {
        "name": VALID_STOCK_OPTION_2,
        "quantity": 10,
        "type": "sell"
    }
    print(f"{(requests.post(URL_ORDERS, json=buyJson)).json()}\n")
    
    # Retrieve all local databases from each order service
    databases = {}
    for orderRepID in ORDER_SERVERS:
        # Get the host and port for the order service
        orderHost, orderPort = ORDER_SERVERS[orderRepID]

        # Format URL to send request for database
        url = f"http://{orderHost}:{orderPort}/dump-database"

        # Add current order service's database to dictionary
        databases[orderRepID] = (requests.get(url)).json()
    
    # Assert that each database contains the same contents
    for i in range(2):
        id = i + 1
        curDatabase = databases[id]
        nextDatabase = databases[id + 1]

        if curDatabase != nextDatabase:
            print("Failed test_consistency")
            print(f"Databases do not match:\n Order {id}: {curDatabase}\n Order {id + 1}: {nextDatabase}\n")
            return (False, 'test_consistency')
    
    print("PASSED: test_consistency")
    print("All databases are consistent among replicas\n")
    return (True, 'test_consistency')

def test_fault_tolerance():
    # Note: Make sure entire app is running when performing this test!
    print("BEGIN: test_fault_tolerance")

    # Get current leader from front end (should be Order service 3)
    getLeaderUrl = f"http://{FRONT_HOST}:{FRONT_PORT}/leader"
    leaderJson = (requests.get(getLeaderUrl)).json()
    curLeaderHost = leaderJson["leader-host"]
    curLeaderPort = leaderJson["leader-port"]

    # Assert that the correct order replica is leader
    try:
        order3Host, order3Port = ORDER_SERVERS[3]
        assert(curLeaderHost == order3Host)
        assert(curLeaderPort == order3Port)

        print("Leader has been assigned correctly by front end\n")
    except:
        print("Failed test_fault_tolerance")
        print("Leader was not correctly chosen, or order service 3 was offline at time of test.")
        print(f"Chosen leader/host: {curLeaderHost, curLeaderPort}\n")
        return (False, 'test_fault_tolerance')
    
    # Send message to shutdown order service 3
    shutdownUrl = f"http://{curLeaderHost}:{curLeaderPort}/shutdown"
    try:
        requests.post(shutdownUrl)
    except (requests.exceptions.ConnectionError, Exception) as e:
        if type(e) == requests.exceptions.ConnectionError:
            print("Order server 3 successfuly shutdown")
        else:
            print("Error occurred while shutting down Order server 3")
            print("Failed test_fault_tolerance")
            return (False, 'test_fault_tolerance')
    
    # Now attempt to send a buy request for a valid stock to prompt leader selection
    buyJson = {
        "name": VALID_STOCK_OPTION_2,
        "quantity": 10,
        "type": "buy"
    }

    # Test if new leader is chosen correctly
    try:
        # Send buy request to front
        buyRes = requests.post(URL_ORDERS, json=buyJson)
        buyResJson = buyRes.json()
        print(f"Successfully received message from order service: {buyResJson}")

        # Get leader from front end
        leaderJson = (requests.get(getLeaderUrl)).json()
        curLeaderHost = leaderJson["leader-host"]
        curLeaderPort = leaderJson["leader-port"]

        # Assert that correct leader was chosen (in the case where 3 was leader, 2 should be next)
        order2Host, order2Port = ORDER_SERVERS[2]
        assert(order2Host == curLeaderHost)
        assert(order2Port == curLeaderPort)
    except:
        print("Failed test_fault_tolerance\n")
        print(f"An error occurred with leader selection: order service 2 was not chosen, or it was offline at the time of test.")
        print(f"Chosen host/port: {curLeaderHost, curLeaderPort}")
        return (False, 'test_fault_tolerance')
    
    # Passed test
    print("PASSED: test_fault_tolerance")
    return (True, 'test_fault_tolerance')

# Run each test
if __name__ == "__main__":
    # List of tests
    # Tests will be run in the order they appear

    """
    IMPORTANT: Make sure all databases have been initialized to their initial state before running the tests!
    """
    tests = [
        test_valid_lookup,
        test_invalid_lookup,
        test_frontend_buy,
        test_frontend_sell,
        test_trade_invalid_stock,
        test_lru_cache,
        test_invalidate,
        test_consistency,
        test_fault_tolerance
    ]

    # Run each test
    numPassed = 0
    numFailed = 0
    failedTests = []
    for test in tests:
        passed, testName = test()
        if passed:
            numPassed += 1
        else:
            numFailed += 1
            failedTests.append(testName)
    
    # Print each test failed
    print('--------------------')
    if numFailed > 0:
        for failedTest in failedTests:
            print(failedTest)
    else:
        print("All passed!")