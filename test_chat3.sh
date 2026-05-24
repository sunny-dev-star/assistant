#!/bin/bash
curl -s -X POST http://localhost:8000/v1/ecommerce/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"热销商品","user_id":"user_001"}' | python3 -m json.tool
