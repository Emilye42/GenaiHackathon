import boto3, os, json

bedrock = boto3.client("bedrock-agent-runtime")

def lambda_handler(event, context):
    agent_id = os.environ["AGENT_ID"]
    agent_alias_id = os.environ["AGENT_ALIAS_ID"]
    input_text = event.get("queryStringParameters", {}).get("q", "Hello")

    response = bedrock.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId="demo-session",
        inputText=input_text
    )

    output = response["completion"]["outputText"]
    return {"statusCode": 200, "body": json.dumps({"response": output})}
