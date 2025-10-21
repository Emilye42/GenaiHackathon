import boto3
import json, hashlib

s3 = boto3.client("s3")

# -------------------------------
# Utility Functions
# -------------------------------

def generate_chunk_id(file_path, json_path):
    """Generate a unique ID for each chunk."""
    base = f"{file_path}:{json_path}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()

def normalize_json_path(path):
    """Normalize JSON paths for readability."""
    return path.replace("[", ".").replace("]", "").replace("..", ".")

def is_entity_like(obj):
    """Decide if an object is an 'entity' worth chunking as one block."""
    if not isinstance(obj, dict):
        return False
    if len(obj) < 2 or len(obj) > 5:
        return False
    nested_count = sum(isinstance(v, (dict, list)) for v in obj.values())
    return nested_count <= 1

def json_to_path_chunks(data, prefix="root", file_name="unknown.json", max_chunks=100):
    """
    Converts JSON into Bedrock KB-compatible chunks.
    Returns a list of dicts with "key", "content", "metadata".
    """
    chunks = []

    def recurse(value, path):
        if isinstance(value, dict):
            if is_entity_like(value):
                chunk_id = generate_chunk_id(file_name, path)
                content = json.dumps(value, indent=2, ensure_ascii=False)
                chunks.append({
                    "key": chunk_id,
                    "content": content,
                    "metadata": {
                        "fileName": file_name,
                        "path": normalize_json_path(path)
                    }
                })
            else:
                for k, v in value.items():
                    recurse(v, f"{path}.{k}")
        elif isinstance(value, list):
            for i, v in enumerate(value):
                recurse(v, f"{path}[{i}]")
        else:
            chunk_id = generate_chunk_id(file_name, path)
            chunks.append({
                "key": chunk_id,
                "content": str(value),
                "metadata": {
                    "fileName": file_name,
                    "path": normalize_json_path(path)
                }
            })

    recurse(data, prefix)
    return chunks[:max_chunks]

# -------------------------------
# Lambda Handler
# -------------------------------

def lambda_handler(event, context):
    """
    Custom KB chunking Lambda:
    - Reads content from S3
    - Applies structured chunking
    - Writes processed chunks back to S3
    - Returns manifest in Bedrock-compatible format
    """
    print(f"📥 Received event: {json.dumps(event)[:500]}")

    input_bucket = event.get("bucketName")
    input_files = event.get("inputFiles", [])
    original_file_location = event.get("originalFileLocation", {})
    output_bucket = "aws-ai-hackathon"  # TODO: parameterize

    if not input_bucket or not input_files:
        raise ValueError("Missing required input parameters: bucketName or inputFiles")

    output_files = []

    for input_file in input_files:
        content_batches = input_file.get("contentBatches", [])
        processed_batches = []

        for batch in content_batches:
            input_key = batch.get("key")
            if not input_key:
                raise ValueError("Missing key in content batch")

            # Read input file from S3
            obj = s3.get_object(Bucket=input_bucket, Key=input_key)
            file_content = obj["Body"].read().decode("utf-8")
            batch_data = json.loads(file_content)

            # Chunk JSON content
            file_chunks = json_to_path_chunks(batch_data, file_name=input_key)

            # Write chunks back to S3
            output_key = f"Output/{input_key}"
            s3.put_object(
                Bucket=output_bucket,
                Key=output_key,
                Body=json.dumps(file_chunks).encode("utf-8")
            )

            # Each batch returned must have a key pointing to the S3 location
            processed_batches.append({
                "key": output_key
            })

        # Return each file as an object containing processed batches
        output_file = {
            "originalFileLocation": original_file_location,
            "contentBatches": processed_batches
        }
        output_files.append(output_file)

    result = {"outputFiles": output_files}
    print(f"🎉 Returning output manifest: {json.dumps(result)[:500]}")
    return result
