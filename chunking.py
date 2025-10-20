import json
import boto3
import os
import hashlib

s3 = boto3.client("s3")

# -------------------------------
# Utility Functions
# -------------------------------

def generate_chunk_id(file_path, json_path):
    base = f"{file_path}:{json_path}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()

def normalize_json_path(path):
    return path.replace("[", ".").replace("]", "").replace("..", ".")

def is_entity_like(obj):
    """Decide if an object is an 'entity' worth chunking as one block."""
    if not isinstance(obj, dict):
        return False
    if len(obj) < 2 or len(obj) > 5:
        return False
    nested_count = sum(isinstance(v, (dict, list)) for v in obj.values())
    return nested_count <= 1

def json_to_path_chunks(data, prefix="root", file_name="unknown.json", max_chunks=1000):
    chunks = []
    def recurse(value, path):
        if isinstance(value, dict):
            if is_entity_like(value):
                chunk_id = generate_chunk_id(file_name, path)
                content = json.dumps(value, indent=2)
                chunks.append({
                    "id": chunk_id,
                    "path": normalize_json_path(path),
                    "content": content,
                    "metadata": {"file_name": file_name, "type": "entity"}
                })
            else:
                for k, v in value.items():
                    recurse(v, f"{path}.{k}")
        elif isinstance(value, list):
            for i, v in enumerate(value):
                recurse(v, f"{path}.{i}")
        else:
            chunk_id = generate_chunk_id(file_name, path)
            chunks.append({
                "id": chunk_id,
                "path": normalize_json_path(path),
                "content": json.dumps(value),
                "metadata": {"file_name": file_name, "type": "field"}
            })
    recurse(data, prefix)
    return chunks[:max_chunks]


# -------------------------------
# Lambda Handler
# -------------------------------

def lambda_handler(event, context):
    """
    Custom Bedrock KB chunking Lambda:
    Reads each contentBatch JSON from the intermediate bucket,
    applies structured chunking, writes processed results to Output/,
    and returns the outputFiles manifest.
    """

    print(f"📥 Received event: {json.dumps(event)[:500]}")

    # Extract bucket name and input file list
    input_bucket = event.get("bucketName")
    input_files = event.get("inputFiles", [])

    if not input_bucket or not input_files:
        raise ValueError("Missing required input parameters: bucketName or inputFiles")

    output_files = []

    for input_file in input_files:
        file_metadata = input_file.get("fileMetadata", {})
        original_file_location = input_file.get("originalFileLocation", {})
        content_batches = input_file.get("contentBatches", [])

        processed_batches = []

        for batch in content_batches:
            input_key = batch.get("key")
            if not input_key:
                raise ValueError("Missing input batch key")

            # Read input batch JSON
            obj = s3.get_object(Bucket=input_bucket, Key=input_key)
            batch_data = json.loads(obj["Body"].read().decode("utf-8"))

            # Perform chunking for each fileContent entry
            chunked_output = {"fileContents": []}
            for content in batch_data.get("fileContents", []):
                content_body = content.get("contentBody", "")
                content_type = content.get("contentType", "text/plain")
                content_metadata = content.get("contentMetadata", {})

                try:
                    parsed = json.loads(content_body)
                except Exception:
                    parsed = {"text": content_body}  # fallback for plain text

                chunks = json_to_path_chunks(parsed, file_name=input_key)

                # Write each chunk as a separate contentBody item
                for ch in chunks:
                    chunked_output["fileContents"].append({
                        "contentType": content_type,
                        "contentMetadata": {**content_metadata, "chunkId": ch["id"], "path": ch["path"]},
                        "contentBody": ch["content"]
                    })

            # Upload processed batch to Output/
            output_key = f"Output/{os.path.basename(input_key)}"
            s3.put_object(
                Bucket=input_bucket,
                Key=output_key,
                Body=json.dumps(chunked_output).encode("utf-8"),
                ContentType="application/json"
            )

            processed_batches.append({"key": output_key})
            print(f"✅ Processed {input_key} -> {output_key} ({len(chunked_output['fileContents'])} chunks)")

        output_files.append({
            "originalFileLocation": original_file_location,
            "fileMetadata": file_metadata,
            "contentBatches": processed_batches
        })

    result = {"outputFiles": output_files}
    print(f"🎉 Returning output manifest: {json.dumps(result)[:500]}")
    return result
e