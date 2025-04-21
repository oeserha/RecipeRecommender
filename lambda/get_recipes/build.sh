#!/bin/bash

# Lambda deployment package creator script
# This script packages a Lambda function with its dependencies

# Set variables
FUNCTION_FILE="lambda_function.py"
PACKAGE_DIR="package"
OUTPUT_ZIP="lambda-deployment.zip"

echo "==== AWS Lambda Deployment Package Creator ===="

# Clean up old files
echo "Cleaning up old files..."
rm -rf "$PACKAGE_DIR"
rm -f "$OUTPUT_ZIP"

# Create package directory
echo "Creating package directory..."
mkdir -p "$PACKAGE_DIR"

# Install dependencies
echo "Installing dependencies to $PACKAGE_DIR..."
pip3 install pinecone -t "$PACKAGE_DIR/"

# Zip dependencies
echo "Packaging dependencies..."
cd "$PACKAGE_DIR"
zip -r "../$OUTPUT_ZIP" .
cd ..

# Add function code to zip
echo "Adding function code to deployment package..."
zip -g "$OUTPUT_ZIP" "$FUNCTION_FILE"

# Report size
ZIP_SIZE=$(du -h "$OUTPUT_ZIP" | cut -f1)
echo "Deployment package created: $OUTPUT_ZIP ($ZIP_SIZE)"
echo "You can now upload this zip file to AWS Lambda"

echo "==== Done ===="