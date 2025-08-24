#!/usr/bin/env python3
import json
import sys

while True:
    try:
        line = sys.stdin.readline()
        if not line:
            break

        req = json.loads(line.strip())
        method = req.get("method", "")
        req_id = req.get("id", 1)

        if method == "initialize":
            response = {"jsonrpc":"2.0","id":req_id,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}}}}
        elif method == "tools/list":
            response = {"jsonrpc":"2.0","id":req_id,"result":{"tools":[{"name":"get_weather","description":"Get Leiria weather","inputSchema":{"type":"object"}}]}}
        elif method == "tools/call":
            response = {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":"Leiria: 18°C, Cloudy, 92% humidity, 5 km/h wind"}]}}
        else:
            response = {"jsonrpc":"2.0","id":req_id,"error":{"code":-32601,"message":"Unknown method"}}

        print(json.dumps(response), flush=True)

    except Exception as e:
        break
