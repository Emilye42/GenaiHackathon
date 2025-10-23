CloudFormation Composer

CloudFormation Composer is an AI-powered tool that helps users generate AWS CloudFormation templates quickly, securely, and according to their company-specific rules. By leveraging natural language input, knowledge bases, and custom chunking logic, the system simplifies infrastructure provisioning for cloud teams.

Features

Natural Language to CloudFormation Templates: Users can input plain language requests to generate ready-to-deploy CloudFormation templates.

Knowledge Base Integration: References company-specific rules, past templates, and AWS documentation to produce compliant templates.

Custom Chunking Logic: Preserves JSON/YAML hierarchical structure when ingesting templates into a vector-based knowledge base.

Secure Deployment: Generates production-ready templates following AWS best practices.

Interactive Agent Access: Provides an AI agent interface accessible via API Gateway and static website hosted on S3.

Architecture Overview

Data Sources

AWS example templates from GitHub

Official AWS CloudFormation user guide PDFs

Data Processing Pipeline

Original files are stored in an S3 bucket

Custom Lambda function chunks JSON/YAML files while preserving hierarchy

Chunked data is stored in a secondary S3 bucket and ingested into a vector knowledge base

Agent Layer

Bedrock agent connected to both knowledge bases

Processes user queries and generates CloudFormation templates or answers questions

Web Interface

Static website hosted in S3

Connects to API Gateway, which triggers the Lambda agent wrapper

Users can interact with the agent via a browser

Usage

Open the hosted static website.

Enter a natural language request, e.g., “Create a CloudFormation template for an SNS topic with email subscription.”

Submit the request.

The agent will return a CloudFormation template along with a brief explanation of what it does and why it is safe/compliant.

Deployment

S3 Hosting: Upload the front-end HTML page to an S3 bucket with static website hosting enabled.

API Gateway: Configure a REST API with routes (/query) and connect it to the Lambda function.

Lambda Function: Deploy the Lambda wrapper function that invokes the Bedrock agent and returns responses in JSON format.

Environment Variables: Set AGENT_ID and AGENT_ALIAS_ID in the Lambda function.

CORS Configuration: Ensure the Lambda function returns CORS headers to allow the browser to call the API.

Example

User Input:

Create a CloudFormation template for an S3 bucket with versioning enabled.


Agent Output:

AWSTemplateFormatVersion: '2010-09-09'
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      VersioningConfiguration:
        Status: Enabled


Explanation:
This template creates an S3 bucket with versioning enabled, ensuring all objects are tracked and previous versions are preserved for recovery purposes.

Requirements

AWS Account with Bedrock and Lambda permissions

S3 bucket for original and chunked files

API Gateway for public access

Knowledge base ingestion via Bedrock

Notes

Templates and PDFs used in training are ingested into separate knowledge bases to maintain context.

Custom chunking preserves the hierarchical structure of templates for better comprehension by the agent.

This project is designed for hackathon demonstration purposes; adapt access control and security for production deployment.
