import boto3
import os
import json

bedrock = boto3.client("bedrock-agent-runtime")
def lambda_handler(event, context):
    # API Gateway HTTP API sends a dict

    # For POST method
    body = json.loads(event.get("body", "{}"))
    text = body.get("query", "Hello")

    agent_id = "P9XSME7NNB"#TODO update agentid and alias to custom
    agent_alias_id = "9WEXNISCVS"
    
    response = bedrock.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId="session-1",
        inputText=text
    )
    output_text = ""
    for e in response.get("completion", []):
        chunk = e.get("chunk", {})
        if "text" in chunk:
            output_text += chunk["text"]
        elif "bytes" in chunk:
            output_text += chunk["bytes"].decode("utf-8")  # <-- decode bytes

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps({"response": output_text})
    }