# RecipeRecommender

### Abstract
In this project, we developed SmartChef, an intelligent recipe recommendation system designed to provide users with personalized meal suggestions based on their dietary preferences, restrictions, and natural language requests. Leveraging a dataset of over 500,000 recipes containing rich metadata—including ingredients, instructions, ratings, and cook times—we convert recipes and user queries into high-dimensional embeddings using a pre-trained BERT model. These embeddings are indexed in a Pinecone vector database, enabling efficient semantic search to retrieve the most relevant recipe recommendations.

The user interacts with the system through a Streamlit web app, where they can build a dietary profile and request personalized recipes. Under the hood, AWS Lambda functions process user input, generate embeddings, query Pinecone, and apply filtering logic based on user-specific constraints. The application backend is supported by AWS API Gateway, S3 for storage, and SageMaker for model inference and selection.

To make the system production-ready, we incorporated automation pipelines for embedding new data, updating user profiles, and deploying model improvements. The system is modular, cloud-native, and designed to support scalable, real-time recommendation services. SmartChef demonstrates the practical application of MLOps principles to deliver a responsive and user-focused AI-powered experience.

### Project Description
- Problem- Choosing what to cook is often frustrating—users waste time searching for meals that fit their preferences, dietary restrictions, and current cravings
- Solution- An intelligent recipe recommendation system that delivers personalized meal ideas based on user profiles, preferences, and real-time input
- How it works-
  - Vector DB with 500k+ embedded recipes with metadata
  - User information such as likes, dislikes, and allergies are collected
  - User requests are embedded along with user info to find recipes to recommend
  - Personalized Results are returned to the user

### New Service Used
- Pinecone vector DB
- EventBridge: used to trigger certain events, such as redoing model selection when triggered by model monitor or to re-embedding recipes based on new model

### Total Cost
Our project ended up costing a total of 18.43, all of which came from Sagemaker costs, particularly from having endpoints and lab instances running.

### Scaling Our Project
Describe how architecture would change
Currently, we use Streamlit for the user interface, which works well for prototyping and demos. To scale, we would replace Streamlit with a React-based frontend deployed via AWS Amplify or CloudFront. This approach provides better performance, load balancing, and global content delivery for end users.
Our backend logic is handled by AWS Lambda functions exposed through API Gateway. This serverless approach scales automatically to support high concurrency. We would separate concerns by using distinct Lambda functions for tasks like user authentication, embedding generation, and recipe recommendation. Caching common queries would reduce load on downstream services.
To generate recipe and query embeddings, we use a BERT-based model deployed with AWS SageMaker. To scale:
- We would use autoscaling endpoints to increase capacity during high demand.
- For cost efficiency, we can use asynchronous inference or SageMaker’s multi-model endpoints.
- To further optimize performance, we could distill or quantize the model to reduce latency.

### Projected Future Work
- Allow users to rate recipes they’ve tried and incorporate those into our model
- Include nutritional information
- Scale to use a larger recipe list
- Add more details to the UI

### Demo Script
See demo.ipynb to see some of the basics of our recommendation system!
