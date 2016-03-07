#!/usr/bin/env bash

# need make to build redis
sudo apt-get update
# sudo apt-get upgrade
sudo apt-get install -y redis-server
sudo sed -i -e 's/bind 127.0.0.1/bind 0.0.0.0/g' /etc/redis/redis.conf
sudo /etc/init.d/redis-server restart
