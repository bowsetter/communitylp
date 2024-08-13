#!/bin/bash

exec python3.10 cron.py &
exec python3.10 main.py
