# Dependencies

Outside of requiring the Python environment and its libraries, the following packages are also required:

- `Flask`: Used for HTTP routing and requests
- Python Dotenv (`python_dotenv`): Used for reading a .env file containing instance variables

# Running the Microservices
### AWS Setup

A single AWS EC2 t2.micro instance can be used to run each microservice. Use the appropriate AWS CLI commands to initialize an EC2 t2.micro instance using the Ubuntu server 18.04 image provided by canonical (ami: ami-0d73480446600f555). Be sure to take note of the public IP address assigned to this instance using the following command: 

    aws ec2 describe-instances --instance-id <instance-id-here>
  
Once the instance has been initialized, SSH into the instance using its public DNS name and install the following: 

- `Git`: Used for cloning this repository to the EC2 instance
- `python3`: Used for running the source code
- `python3-pip`: Used for downloading python dependencies
- `tmux`: Terminal multiplexer that can be used to run each microservice in parallel. Documentation for using `tmux` can be found [here](https://github.com/tmux/tmux/wiki/Getting-Started)
- `vim`/`emacs`/`nano`/`text editor of your choice`: Used to modify the included .env file 

Once each of these programs has been installed, clone this repository to the EC2 instance, download the python dependencies using `pip`, and begin a new `tmux` session using the `tmux` command. With the new `tmux` session started, create a total of 5 windows: one for each microservice.

In addition, before starting any of the microservices, use the text editor you installed to modify the provided .env file by replacing the values for the variables `CATALOG_HOST`, `FRONT_HOST`, and each `ORDER_<id>_HOST` variable with the public IP address for the EC2 instance. The .env file can be found in the root of the `src` directory for this repository. Additionally, adjust the ports as necessary, and make sure each is authorized for connections.

### Running the Front End Service

To run the front end service, use any one of the available `tmux` windows and `cd` into the `src/front-end` directory. The following command may be used to start the front end service: 

    python3 FrontEndServer.py <cache-flag>

The `<cache-flag>` parameter can be set to either 0 or 1, with 0 denoting that the front end should not cache the result of stock lookups, and 1 denoting that stock lookups should be cached. 

### Running the Order Service Replicas

To run the order service replicas, use any 3 of the available `tmux` windows and `cd` into the `src/orders` directory. The following command may be used to start an order service replica: 

    python3 OrderServer.py <server-id>

The `<server-id>` parameter can be set to 1, 2, or 3. However, each instance of an order server replica __must__ have a unique ID.

## Running the Catalog Service

To run the catalog service, use any available `tmux` window that is not being used by the front end and the order services, and use the following command to start the service: 
    
    python3 CatalogServer.py <cache-flag>

Like the `<cache-flag>` parameter for the front end service, 0 denotes that the application will not be using a cache to store stock lookups, and 1 denotes that the application will be using a cache to store lookups.

# Running the Client

This part assumes you are using `bash` or `git bash`. To run the client, simply clone this repository to your local machine and `cd` into the `src/client` directory. A shell script has been provided in this folder that can be used to run multiple clients concurrently. The shell script may be invoked using the following command: 

    ./ClientRun.sh <num-clients> <trade-probability> <num-requests> <host> <port>

The flags are as follows: 

- `<num-clients>`: Number of clients to run
- `<trade-probability>`: Probability that a trade request will be issued when a stock is looked up, assuming it has non-zero shares remaining
- `<num-requests>`: Number of requests to send over a session
- `<host>`: Host IP of front end service
- `<port>`: Port of front end service

# Running the Tests

Tests can be located in the `src/test` directory. The following files are provided in the directory:

- `AppTest.py`: Used for testing the entire application
- `OrderTest.py`: Used for testing the order service
- `CatalogTest.py`: Used for testing the catalog service

To run each test properly, make sure each component is running (on AWS or your local machine) and the .env file is configured appropriately before running each python file. In addition, be sure to read the comments in each test file for any additional setup instructions.

    python3 <name-of-test>.py
