#!/bin/bash

# Number of clients to run
numClients=$1

# Probability of performing a trade
prob=$2

# Number of repetitions
reps=$3

# Host and port to connect to
hostName=$4
port=$5

for ((i=1; i<=$numClients; ++i))
do
    # Call ClientScript.py
    python ClientScript.py $prob $reps $hostName $port $i &
done
wait